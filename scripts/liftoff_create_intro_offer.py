"""Create an Introductory Offer on Liftoff Yearly subscription.

70% off yearly ($24.99 -> $7.49) as PAY_UP_FRONT for 1 year, all territories,
starting today, ending July 31 2026.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

import jwt

ASC_BASE = "https://api.appstoreconnect.apple.com/v1"

SUB_ID = "6776393232"  # yearly
START_DATE = "2026-07-01"
END_DATE = "2026-07-31"

# Apple price points are represented by price IDs, not raw dollars.
# We must find the Tier that corresponds to ~$7.49 USD, then find the equivalent
# in all territories the sub is offered in.

# Full price is $24.99 -> tier 25 in old system, but the new system uses price points.
# We'll fetch the subscription's available price points and pick the one closest to
# 7.49 USD.

TARGET_USD = 7.49


def load_env() -> tuple[str, str, str]:
    return (
        os.environ["APP_STORE_CONNECT_KEY_ID"],
        os.environ["APP_STORE_CONNECT_ISSUER_ID"],
        os.environ["APP_STORE_CONNECT_PRIVATE_KEY"],
    )


def make_token(key_id: str, issuer_id: str, private_key: str) -> str:
    now = int(time.time())
    payload = {
        "iss": issuer_id,
        "iat": now,
        "exp": now + 20 * 60,
        "aud": "appstoreconnect-v1",
    }
    return jwt.encode(payload, private_key, algorithm="ES256",
                      headers={"kid": key_id, "typ": "JWT"})


def req(token: str, method: str, path: str, body: dict | None = None) -> dict:
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


def get_all(token: str, path: str) -> list[dict]:
    out: list[dict] = []
    url = f"{ASC_BASE}{path}"
    while url:
        resp = req(token, "GET", url if url.startswith("http") else url)
        out.extend(resp.get("data", []))
        url = resp.get("links", {}).get("next")
    return out


def main() -> None:
    key_id, issuer_id, private_key = load_env()
    token = make_token(key_id, issuer_id, private_key)

    # 1. Fetch all price points for the subscription in USD to pick target price point
    print(f"Fetching price points for sub {SUB_ID}...")
    # subscriptionPricePoints endpoint requires filter[territory]
    price_points = get_all(
        token,
        f"/subscriptions/{SUB_ID}/pricePoints?filter[territory]=USA&limit=200",
    )
    print(f"  {len(price_points)} USA price points fetched")

    if not price_points:
        print("ERROR: no price points; check subscription state.", file=sys.stderr)
        sys.exit(1)

    # Find closest to TARGET_USD
    def parse_price(pp: dict) -> float:
        return float(pp["attributes"]["customerPrice"])

    price_points.sort(key=lambda pp: abs(parse_price(pp) - TARGET_USD))
    target_pp = price_points[0]
    target_price = parse_price(target_pp)
    print(f"  Chosen USA price point: id={target_pp['id']}, price=${target_price}")

    if abs(target_price - TARGET_USD) > 1.5:
        print(f"WARN: closest price point ${target_price} is far from target ${TARGET_USD}",
              file=sys.stderr)

    # Extract the priceTier / equalizations to apply across all territories.
    # Approach: use "equalizations" endpoint on that price point to find the equivalent
    # in every other territory.
    print("Fetching territory equalizations for chosen price point...")
    equalizations = get_all(
        token,
        f"/subscriptionPricePoints/{target_pp['id']}/equalizations?limit=200",
    )
    print(f"  {len(equalizations)} territory equalizations")

    # Build the prices array for introductoryOffer
    prices_data = []
    # Include the USA price point itself
    prices_data.append({
        "type": "subscriptionPricePoints",
        "id": target_pp["id"],
    })
    for eq in equalizations:
        if eq["id"] != target_pp["id"]:
            prices_data.append({
                "type": "subscriptionPricePoints",
                "id": eq["id"],
            })

    # 2. Create the introductory offer
    print(f"\nCreating introductory offer: {START_DATE} to {END_DATE}, PAY_UP_FRONT, 1YEAR")

    # For introductoryOffers, the payload wants:
    # - relationships.subscription
    # - relationships.subscriptionPricePoint (single, for the base territory USA)
    # - startDate, endDate (optional), offerMode, duration, numberOfPeriods
    # We need to create one per territory OR one with allTerritories=true.
    # ASC API supports creating one introductoryOffer with territory filter.
    # For a global offer across all territories, we omit territory and pass
    # subscriptionPricePoint per-territory. Actually the API creates one offer per
    # (subscription, territory) pair — we loop.

    created = 0
    skipped = 0
    failed = 0

    for pp_ref in prices_data:
        pp_id = pp_ref["id"]
        # Fetch price point to learn its territory
        pp_detail = req(token, "GET",
                        f"/subscriptionPricePoints/{pp_id}?include=territory")
        territory_id = None
        for inc in pp_detail.get("included", []):
            if inc["type"] == "territories":
                territory_id = inc["id"]
        if not territory_id:
            # Fall back to relationships
            territory_id = (pp_detail["data"]["relationships"]
                            .get("territory", {}).get("data", {}).get("id"))
        if not territory_id:
            print(f"  skip {pp_id}: no territory", file=sys.stderr)
            skipped += 1
            continue

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
                        "data": {"type": "subscriptionPricePoints", "id": pp_id}
                    },
                    "territory": {
                        "data": {"type": "territories", "id": territory_id}
                    },
                },
            }
        }
        try:
            resp = req(token, "POST", "/subscriptionIntroductoryOffers", body)
            print(f"  OK: territory={territory_id}, offer id={resp['data']['id']}")
            created += 1
        except urllib.error.HTTPError as e:
            failed += 1
            if failed >= 5 and created == 0:
                print("Too many failures, aborting.", file=sys.stderr)
                raise

    print(f"\nDone. created={created} skipped={skipped} failed={failed}")


if __name__ == "__main__":
    main()
