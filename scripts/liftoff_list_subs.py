"""List subscription groups and subscriptions for Liftoff app."""
import json
import os
import sys
import time
import urllib.request
import urllib.error
import jwt

APP_ID = "6776392285"
ASC_BASE = "https://api.appstoreconnect.apple.com/v1"

key_id = os.environ["APP_STORE_CONNECT_KEY_ID"]
issuer_id = os.environ["APP_STORE_CONNECT_ISSUER_ID"]
private_key = os.environ["APP_STORE_CONNECT_PRIVATE_KEY"]

now = int(time.time())
payload = {"iss": issuer_id, "iat": now, "exp": now + 20*60, "aud": "appstoreconnect-v1"}
token = jwt.encode(payload, private_key, algorithm="ES256", headers={"kid": key_id, "typ": "JWT"})

def req(url):
    r = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(r) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"ERR {e.code}: {e.read().decode()[:500]}", file=sys.stderr)
        raise

# Get app details
app = req(f"{ASC_BASE}/apps/{APP_ID}")
print(f"App: {app['data']['attributes'].get('name')} ({app['data']['attributes'].get('bundleId')})")

# Get subscription groups
groups = req(f"{ASC_BASE}/apps/{APP_ID}/subscriptionGroups?include=subscriptions")
print(f"\nSubscription groups: {len(groups['data'])}")
for g in groups['data']:
    print(f"  Group id: {g['id']}, refName: {g['attributes'].get('referenceName')}")
    sub_ids = [s['id'] for s in g['relationships']['subscriptions']['data']]
    print(f"    subs: {sub_ids}")

for item in groups.get('included', []):
    if item['type'] == 'subscriptions':
        a = item['attributes']
        print(f"\n  Sub id: {item['id']}")
        print(f"    productId: {a.get('productId')}")
        print(f"    name: {a.get('name')}")
        print(f"    duration: {a.get('subscriptionPeriod')}")
        print(f"    state: {a.get('state')}")
