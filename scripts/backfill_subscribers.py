#!/usr/bin/env python3
"""
One-shot backfill of state/subscribers_history.csv.

Reconstructs daily subscriber counts back ~90 days using:
- App Store Connect DAILY SUBSCRIPTION reports for iOS Plus active subscribers
- Kit /v4/subscribers (paginated) with created_at to derive cumulative
  newsletter subscriber count per day

Play Store backfill is intentionally skipped — we don't yet have a daily
active-subscriber report wired (only event-based 30d delta), so historical
reconstruction would be inaccurate. Play counts will start being logged
going forward via dashboard_refresh.py.

Idempotent: upserts by date. Safe to re-run.

Env vars required:
  KIT_API_KEY
  APP_STORE_CONNECT_KEY_ID, APP_STORE_CONNECT_ISSUER_ID,
  APP_STORE_CONNECT_PRIVATE_KEY, APP_STORE_CONNECT_VENDOR_NUMBER

Usage:
  python scripts/backfill_subscribers.py [--days 90]
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
HISTORY_CSV = REPO_ROOT / "state" / "subscribers_history.csv"

sys.path.insert(0, str(SCRIPTS))

from subscriber_history import FIELDS  # noqa: E402


def log(msg: str):
    print(msg, file=sys.stderr, flush=True)


# ---------- Kit cumulative newsletter subs ----------
def fetch_kit_created_dates() -> dict[str, int]:
    """Return {YYYY-MM-DD: subscribers_created_that_day} for ALL active subs.

    Kit /v4/subscribers returns created_at per subscriber. We walk all pages
    and bucket by UTC date. Excludes inactive (unsubscribed) — meaning the
    cumulative curve approximates "currently active" rather than gross signups.
    """
    api_key = os.environ.get("KIT_API_KEY")
    if not api_key:
        raise RuntimeError("KIT_API_KEY missing")

    headers = {"X-Kit-Api-Key": api_key, "Accept": "application/json"}
    buckets: dict[str, int] = {}
    cursor = None
    page = 0
    while True:
        url = "https://api.kit.com/v4/subscribers?status=active&per_page=500"
        if cursor:
            url += f"&after={cursor}"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=60) as r:
            import json
            d = json.loads(r.read())
        subs = d.get("subscribers", [])
        for s in subs:
            ca = s.get("created_at") or ""
            day = ca[:10]
            if day:
                buckets[day] = buckets.get(day, 0) + 1
        page += 1
        pag = d.get("pagination", {})
        if pag.get("has_next_page"):
            cursor = pag["end_cursor"]
        else:
            break
        if page > 50:  # safety
            break
    log(f"Kit: fetched {sum(buckets.values())} active subs across {len(buckets)} signup days ({page} pages)")
    return buckets


def kit_cumulative_series(start: date, end: date) -> dict[str, int]:
    """Map date -> cumulative active newsletter subs as of that date."""
    buckets = fetch_kit_created_dates()
    series: dict[str, int] = {}
    cum = 0
    # Pre-roll cumulative from earliest signup up to start date
    earliest = min(buckets.keys()) if buckets else start.isoformat()
    cur = date.fromisoformat(earliest)
    while cur <= end:
        cum += buckets.get(cur.isoformat(), 0)
        if cur >= start:
            series[cur.isoformat()] = cum
        cur += timedelta(days=1)
    return series


# ---------- ASC iOS Plus daily active ----------
def fetch_ios_active_series(start: date, end: date) -> dict[str, int]:
    """Fetch ASC DAILY SUBSCRIPTION reports and return {date: active_total}."""
    import dashboard_sources as ds

    key_id = os.environ.get("APP_STORE_CONNECT_KEY_ID")
    issuer_id = os.environ.get("APP_STORE_CONNECT_ISSUER_ID")
    private_key = os.environ.get("APP_STORE_CONNECT_PRIVATE_KEY")
    vendor_number = os.environ.get("APP_STORE_CONNECT_VENDOR_NUMBER")
    if not (key_id and issuer_id and private_key and vendor_number):
        raise RuntimeError("ASC credentials missing")

    token = ds._asc_jwt(key_id, issuer_id, private_key)
    headers = {"Authorization": f"Bearer {token}"}

    # Find Artemis app id
    apps = ds._http_get(
        "https://api.appstoreconnect.apple.com/v1/apps?limit=20", headers
    )
    app_id = ""
    for a in apps.get("data", []):
        if "artemis" in a.get("attributes", {}).get("name", "").lower():
            app_id = a["id"]
            break

    series: dict[str, int] = {}
    cur = start
    missing = 0
    while cur <= end:
        rd = cur.isoformat()
        rows = ds._fetch_asc_subscription_status(token, vendor_number, app_id, rd)
        if rows:
            summary = ds._summarize_asc_subscription_status(rows)
            series[rd] = summary["active_total"]
        else:
            missing += 1
        cur += timedelta(days=1)
    log(f"ASC iOS: fetched {len(series)} days, {missing} missing/empty")
    return series


# ---------- Merge + write ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90, help="Days back to backfill (default 90)")
    ap.add_argument("--end-offset", type=int, default=2, help="Days back to use as end (ASC has 1-2d lag)")
    args = ap.parse_args()

    today = datetime.now(timezone.utc).date()
    end = today - timedelta(days=args.end_offset)
    start = end - timedelta(days=args.days)
    log(f"Backfilling {start} → {end} ({args.days} days)")

    # Kit cumulative
    try:
        kit_series = kit_cumulative_series(start, end)
    except Exception as e:
        log(f"Kit backfill failed: {e}")
        kit_series = {}

    # iOS Plus daily
    try:
        ios_series = fetch_ios_active_series(start, end)
    except Exception as e:
        log(f"ASC backfill failed: {e}")
        ios_series = {}

    # Load existing rows, build map
    existing: dict[str, dict] = {}
    if HISTORY_CSV.exists():
        with HISTORY_CSV.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                existing[r["date"]] = r

    # Merge: only overwrite kit_active / ios_active / plus_active / total
    # for dates inside backfill window. Preserve play_active if already set.
    written = 0
    cur = start
    while cur <= end:
        d = cur.isoformat()
        kit_val = kit_series.get(d)
        ios_val = ios_series.get(d)

        if kit_val is None and ios_val is None:
            cur += timedelta(days=1)
            continue

        existing_row = existing.get(d, {})
        play_active_raw = existing_row.get("play_active", "")
        try:
            play_val = int(play_active_raw) if play_active_raw not in ("", None) else None
        except (ValueError, TypeError):
            play_val = None

        plus_total = None
        if ios_val is not None or play_val is not None:
            plus_total = (ios_val or 0) + (play_val or 0)

        total = (kit_val or 0) + (plus_total or 0)

        existing[d] = {
            "date": d,
            "kit_active": kit_val if kit_val is not None else "",
            "plus_active": plus_total if plus_total is not None else "",
            "ios_active": ios_val if ios_val is not None else "",
            "play_active": play_val if play_val is not None else "",
            "total": total,
        }
        written += 1
        cur += timedelta(days=1)

    # Write back sorted
    HISTORY_CSV.parent.mkdir(parents=True, exist_ok=True)
    rows_sorted = sorted(existing.values(), key=lambda r: r["date"])
    with HISTORY_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows_sorted)

    log(f"Backfill complete: wrote {written} rows, total {len(rows_sorted)} in CSV")
    log(f"Date range in CSV: {rows_sorted[0]['date']} → {rows_sorted[-1]['date']}")


if __name__ == "__main__":
    main()
