"""TEST: Create Introductory Offer on Liftoff Yearly — USA only, single territory.

Once this works, we scale to all territories.
"""
from __future__ import annotations
import json, os, sys, time, urllib.error, urllib.request
import jwt

ASC_BASE = "https://api.appstoreconnect.apple.com/v1"
SUB_ID = "6776393232"
START_DATE = "2026-07-01"
END_DATE = "2026-07-31"
TARGET_USD = 7.49


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
        print(e.read().decode()[:3000], file=sys.stderr)
        raise


def main():
    token = make_token()

    # 1. Get USA price points
    print("Fetching USA price points...")
    url = f"/subscriptions/{SUB_ID}/pricePoints?filter[territory]=USA&limit=200"
    resp = req(token, "GET", url)
    pps = resp.get("data", [])
    while resp.get("links", {}).get("next"):
        resp = req(token, "GET", resp["links"]["next"])
        pps.extend(resp.get("data", []))
    print(f"  {len(pps)} USA price points")

    if not pps:
        print("ERROR: no USA price points", file=sys.stderr)
        sys.exit(1)

    # Show the range and target
    def price(pp):
        return float(pp["attributes"]["customerPrice"])
    pps_sorted = sorted(pps, key=price)
    print(f"  Range: ${price(pps_sorted[0])} - ${price(pps_sorted[-1])}")

    # Show a few near the target
    near = sorted(pps, key=lambda pp: abs(price(pp) - TARGET_USD))[:5]
    print(f"  Near ${TARGET_USD}:")
    for pp in near:
        print(f"    id={pp['id']} price=${price(pp)}")

    target = near[0]
    print(f"\nChosen: id={target['id']} price=${price(target)}")

    # 2. Get its territory ID
    pp_detail = req(token, "GET",
                    f"/subscriptionPricePoints/{target['id']}?include=territory")
    territory_id = pp_detail["data"]["relationships"]["territory"]["data"]["id"]
    print(f"  Territory: {territory_id}")

    # 3. Try to create the introductory offer
    body = {
        "data": {
            "type": "subscriptionIntroductoryOffers",
            "attributes": {
                "startDate": START_DATE,
                "endDate": END_DATE,
                "duration": "ONE_YEAR",
                "offerMode": "PAY_UP_FRONT",
                "numberOfPeriods": 1,
            },
            "relationships": {
                "subscription": {
                    "data": {"type": "subscriptions", "id": SUB_ID}
                },
                "subscriptionPricePoint": {
                    "data": {"type": "subscriptionPricePoints", "id": target["id"]}
                },
                "territory": {
                    "data": {"type": "territories", "id": territory_id}
                },
            },
        }
    }
    print("\nRequest body:")
    print(json.dumps(body, indent=2))
    print()

    resp = req(token, "POST", "/subscriptionIntroductoryOffers", body)
    print("SUCCESS:")
    print(json.dumps(resp, indent=2)[:2000])


if __name__ == "__main__":
    main()
