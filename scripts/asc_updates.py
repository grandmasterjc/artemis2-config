#!/usr/bin/env python3
"""Read-only report: how many devices download each app update?

Apple's sales reports count every download of the app, split into first
downloads, redownloads and updates, with the app version on each row.
An update is counted when a device downloads it, whether or not the
owner ever opens the app. That is the number Google Analytics cannot
give, because it only sees devices that open the app.

Prints tables to the log. Writes nothing and sends nothing.
"""
import gzip
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dashboard_sources import _asc_jwt  # noqa: E402

FIRST = {"1", "1F", "1T", "F1"}
AGAIN = {"3", "3F", "3T", "F3"}
UPDATE = {"7", "7F", "7T", "F7"}


def fetch(token, vendor, frequency, report_date):
    """(rows, note). note is "" when the report was read."""
    url = (
        "https://api.appstoreconnect.apple.com/v1/salesReports"
        f"?filter%5Bfrequency%5D={frequency}"
        "&filter%5BreportType%5D=SALES"
        "&filter%5BreportSubType%5D=SUMMARY"
        f"&filter%5BvendorNumber%5D={vendor}"
        f"&filter%5BreportDate%5D={report_date}"
        "&filter%5Bversion%5D=1_1"
    )
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/a-gzip, application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        return [], f"no report (HTTP {e.code})"
    except Exception as e:
        return [], f"failed ({type(e).__name__})"
    try:
        text = gzip.decompress(raw).decode("utf-8")
    except Exception:
        return [], "unreadable"
    lines = text.splitlines()
    if len(lines) < 2:
        return [], "empty"
    header = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        cells = line.split("\t")
        if len(cells) == len(header):
            rows.append(dict(zip(header, cells)))
    return rows, ""


def tally(rows):
    """Counts for the Artemis app only: first, again, updates by version."""
    first = again = 0
    updates = defaultdict(int)
    other = defaultdict(int)
    for row in rows:
        name = ((row.get("Title") or "") + " " + (row.get("SKU") or "")).lower()
        if "artemis" not in name:
            continue
        kind = (row.get("Product Type Identifier") or "").strip()
        try:
            units = int(float(row.get("Units") or 0))
        except ValueError:
            units = 0
        if kind in FIRST:
            first += units
        elif kind in AGAIN:
            again += units
        elif kind in UPDATE:
            updates[(row.get("Version") or "?").strip()] += units
        elif not kind.startswith("IA"):
            other[kind] += units
    return first, again, updates, other


def main():
    key_id = os.environ.get("APP_STORE_CONNECT_KEY_ID")
    issuer = os.environ.get("APP_STORE_CONNECT_ISSUER_ID")
    key = os.environ.get("APP_STORE_CONNECT_PRIVATE_KEY")
    vendor = os.environ.get("APP_STORE_CONNECT_VENDOR_NUMBER")
    if not (key_id and issuer and key and vendor):
        print("App Store Connect credentials missing", file=sys.stderr)
        sys.exit(1)
    token = _asc_jwt(key_id, issuer, key)
    today = date.today()
    unknown = defaultdict(int)

    print("=== Per day, last 35 days (Apple's daily reports) ===")
    print(f"{'day':<12}{'first':>8}{'again':>8}{'updates':>9}  updates by version")
    window = defaultdict(int)
    for back in range(35, 0, -1):
        day = today - timedelta(days=back)
        label = day.isoformat()
        rows, note = fetch(token, vendor, "DAILY", label)
        if note:
            print(f"{label:<12}{note}")
            continue
        first, again, updates, other = tally(rows)
        for k, v in other.items():
            unknown[k] += v
        for v, n in updates.items():
            window[v] += n
        split = ", ".join(f"{v}: {n}" for v, n in sorted(updates.items()))
        print(f"{label:<12}{first:>8}{again:>8}{sum(updates.values()):>9}  {split}")

    print()
    print("=== Updates by version, last 35 days ===")
    for v, n in sorted(window.items()):
        print(f"{v:<10}{n:>8}")
    if unknown:
        print()
        print("Product types not counted above:", dict(unknown))


if __name__ == "__main__":
    main()
