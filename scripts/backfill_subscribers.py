#!/usr/bin/env python3
"""TEMPORARY diagnostic (branch claude/dashboard-diag only, never merged).

Shows what App Store Connect answers for the sales and subscription reports
the dashboard uses, because dashboard_sources.py swallows HTTP errors.
Read-only. Prints status codes and Apple's error text, never secrets.
"""
import gzip, json, os, sys, urllib.error, urllib.request
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard_sources import _asc_jwt

key_id = os.environ.get("APP_STORE_CONNECT_KEY_ID", "")
issuer = os.environ.get("APP_STORE_CONNECT_ISSUER_ID", "")
pkey = os.environ.get("APP_STORE_CONNECT_PRIVATE_KEY", "")
vendor = os.environ.get("APP_STORE_CONNECT_VENDOR_NUMBER", "")
print(f"vendor number set={bool(vendor)} length={len(vendor)} digits_only={vendor.strip().isdigit()} has_whitespace={vendor != vendor.strip()}")
token = _asc_jwt(key_id, issuer, pkey)

def get(url):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}", "Accept": "application/a-gzip, application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()

st, body = get("https://api.appstoreconnect.apple.com/v1/apps?limit=5&fields%5Bapps%5D=bundleId,name")
print("apps:", st, [ (a["id"], a["attributes"].get("bundleId")) for a in json.loads(body).get("data", [])] if st == 200 else body[:300])

def report(rtype, version, date, freq="DAILY"):
    url = ("https://api.appstoreconnect.apple.com/v1/salesReports"
           f"?filter%5Bfrequency%5D={freq}&filter%5BreportType%5D={rtype}&filter%5BreportSubType%5D=SUMMARY"
           f"&filter%5BvendorNumber%5D={vendor.strip()}&filter%5BreportDate%5D={date}&filter%5Bversion%5D={version}")
    st, body = get(url)
    if st == 200:
        try:
            lines = gzip.decompress(body).decode().splitlines()
            apps = sorted({l.split("\t")[0] for l in lines[1:]}) if rtype != "SALES" else len(lines) - 1
            return f"200 rows={len(lines)-1} info={apps}"
        except Exception as e:
            return f"200 undecodable {e}"
    try:
        errs = json.loads(body).get("errors", [])
        return f"{st} " + " | ".join(f"{e.get('code')}: {e.get('detail')}" for e in errs)
    except Exception:
        return f"{st} {body[:200]!r}"

for d in ["2026-09-28", "2026-09-30", "2026-10-01", "2026-10-02", "2026-10-07", "2026-10-12", "2026-10-13"]:
    print(d, "SALES:", report("SALES", "1_1", d))
    print(d, "SUBSCRIPTION:", report("SUBSCRIPTION", "1_3", d))
    print(d, "SUBSCRIPTION_EVENT:", report("SUBSCRIPTION_EVENT", "1_3", d))
