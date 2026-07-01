"""List existing introductory offers on Liftoff Yearly."""
import json, os, sys, time, urllib.error, urllib.request
import jwt

ASC_BASE = "https://api.appstoreconnect.apple.com/v1"
SUB_ID = "6776393232"


def make_token():
    now = int(time.time())
    payload = {"iss": os.environ["APP_STORE_CONNECT_ISSUER_ID"], "iat": now,
               "exp": now + 20*60, "aud": "appstoreconnect-v1"}
    return jwt.encode(payload, os.environ["APP_STORE_CONNECT_PRIVATE_KEY"],
                      algorithm="ES256",
                      headers={"kid": os.environ["APP_STORE_CONNECT_KEY_ID"], "typ": "JWT"})


def req(token, method, path):
    url = f"{ASC_BASE}{path}" if path.startswith("/") else path
    r = urllib.request.Request(url, method=method, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(r) as resp:
        return json.loads(resp.read())


def main():
    token = make_token()
    resp = req(token, "GET",
               f"/subscriptions/{SUB_ID}/introductoryOffers?limit=200&include=territory,subscriptionPricePoint")
    print(f"Total: {len(resp['data'])}")
    for off in resp["data"]:
        a = off["attributes"]
        r = off.get("relationships") or {}
        terr_rel = r.get("territory") or {}
        terr = (terr_rel.get("data") or {}).get("id", "?")
        pp_rel = r.get("subscriptionPricePoint") or {}
        pp = (pp_rel.get("data") or {}).get("id", "?")
        print(f"  id={off['id']} territory={terr} start={a.get('startDate')} "
              f"end={a.get('endDate')} mode={a.get('offerMode')} "
              f"duration={a.get('duration')} periods={a.get('numberOfPeriods')} "
              f"pp={pp}")
    print("\nRaw first offer:")
    if resp["data"]:
        print(json.dumps(resp["data"][0], indent=2))

    # Show USA-specific price from included
    print("\nUSA offer price detail:")
    for inc in resp.get("included", []):
        if inc["type"] == "subscriptionPricePoints":
            a = inc["attributes"]
            terr = inc["relationships"]["territory"]["data"]["id"]
            if terr == "USA":
                print(f"  pp id={inc['id']} price=${a['customerPrice']}")


if __name__ == "__main__":
    main()
