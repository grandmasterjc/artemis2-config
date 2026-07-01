"""Set Liftoff Yearly subscription price across all territories.

Usage:
  python liftoff_set_yearly_price.py --usd 7.49 --start 2026-07-01 --end 2026-07-31
  python liftoff_set_yearly_price.py --usd 24.99 --start 2026-08-01

Logic:
  1. Fetch USA price point closest to target USD.
  2. Fetch equalizations across all territories for that USA price point.
     (These are Apple's own conversion tiers — same relative price in each country.)
  3. Post a new subscriptionPrice for every (subscription, territory) pair with:
       - startDate = --start
       - endDate = --end (optional; omit for permanent)
       - preserveCurrentPrice = true (existing subscribers keep old price on price DECREASE;
         on price INCREASE, we should set this false so they follow the schedule up too,
         but Apple requires explicit consent for hikes — so we always keep existing subs
         on their current price)
       - subscriptionPricePoint = territory-equalized point

We upload as a single "subscription price changes" batch using PATCH with append semantics.
"""
from __future__ import annotations
import argparse, json, os, sys, time, urllib.error, urllib.request
import jwt

ASC_BASE = "https://api.appstoreconnect.apple.com/v1"
SUB_ID = "6776393232"  # Liftoff Yearly


def make_token():
    now = int(time.time())
    payload = {"iss": os.environ["APP_STORE_CONNECT_ISSUER_ID"], "iat": now,
               "exp": now + 20*60, "aud": "appstoreconnect-v1"}
    return jwt.encode(payload, os.environ["APP_STORE_CONNECT_PRIVATE_KEY"],
                      algorithm="ES256",
                      headers={"kid": os.environ["APP_STORE_CONNECT_KEY_ID"], "typ": "JWT"})


def req(token, method, path, body=None):
    url = f"{ASC_BASE}{path}" if path.startswith("/") else path
    data = json.dumps(body).encode() if body else None
    headers = {"Authorization": f"Bearer {token}"}
    if body:
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(r) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code} on {method} {path}", file=sys.stderr)
        print(e.read().decode()[:2000], file=sys.stderr)
        raise


def get_all(token, path):
    out = []
    url = f"{ASC_BASE}{path}"
    while url:
        resp = req(token, "GET", url if url.startswith("http") else url)
        out.extend(resp.get("data", []))
        url = resp.get("links", {}).get("next")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--usd", type=float, required=True,
                    help="Target USD price to find matching USA price point")
    ap.add_argument("--start", required=True, help="YYYY-MM-DD start date")
    ap.add_argument("--end", default=None, help="YYYY-MM-DD end date (optional)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--preserve-current-price", default="true",
                    help="true (default) means existing subs keep old price")
    args = ap.parse_args()

    token = make_token()

    # 1. Find USA price point for target USD
    print(f"Fetching USA price points for target ${args.usd}...")
    pps = get_all(token,
                  f"/subscriptions/{SUB_ID}/pricePoints?filter[territory]=USA&limit=200")
    print(f"  {len(pps)} USA price points fetched")

    def price(pp):
        return float(pp["attributes"]["customerPrice"])

    pps_sorted = sorted(pps, key=lambda pp: abs(price(pp) - args.usd))
    target_pp = pps_sorted[0]
    print(f"  Chosen USA pp: id={target_pp['id']}, price=${price(target_pp)}")

    if abs(price(target_pp) - args.usd) > 0.51:
        print(f"WARN: closest USA price ${price(target_pp)} differs from target ${args.usd} "
              f"by more than $0.50", file=sys.stderr)

    # 2. Get equalizations — matching price point across all territories
    print("Fetching territory equalizations...")
    equals = get_all(token, f"/subscriptionPricePoints/{target_pp['id']}/equalizations?limit=200")
    print(f"  {len(equals)} equalizations")

    # Include target USA point itself
    all_price_points = [target_pp] + [e for e in equals if e["id"] != target_pp["id"]]
    print(f"  Total price points to apply: {len(all_price_points)}")

    if args.dry_run:
        print("\nDRY RUN — showing first 5 territories:")
        for pp in all_price_points[:5]:
            terr = pp["relationships"]["territory"]["data"]["id"]
            print(f"    {terr}: pp={pp['id']} price=${price(pp)}")
        return

    # 3. Create subscription price schedule for each territory
    preserve = args.preserve_current_price.lower() == "true"

    ok = 0
    fail = 0
    for pp in all_price_points:
        terr = pp["relationships"]["territory"]["data"]["id"]
        body = {
            "data": {
                "type": "subscriptionPrices",
                "attributes": {
                    "startDate": args.start,
                    "endDate": args.end,
                    "preserveCurrentPrice": preserve,
                },
                "relationships": {
                    "subscription": {
                        "data": {"type": "subscriptions", "id": SUB_ID}
                    },
                    "subscriptionPricePoint": {
                        "data": {"type": "subscriptionPricePoints", "id": pp["id"]}
                    },
                    "territory": {
                        "data": {"type": "territories", "id": terr}
                    },
                },
            }
        }
        try:
            req(token, "POST", "/subscriptionPrices", body)
            ok += 1
            if ok % 20 == 0:
                print(f"  progress: {ok}/{len(all_price_points)}")
        except urllib.error.HTTPError as e:
            fail += 1
            print(f"  FAIL {terr}: {e.code}", file=sys.stderr)
            if fail >= 5 and ok == 0:
                print("Too many failures, aborting.", file=sys.stderr)
                raise

    print(f"\nDone. ok={ok} fail={fail}")


if __name__ == "__main__":
    main()
