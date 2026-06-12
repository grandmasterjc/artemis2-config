#!/usr/bin/env python3
"""
Dashboard refresh: fetch GA4 + Kit data, render dashboard HTML, commit.

Designed for GitHub Actions. Reads credentials from env-vars:
- GOOGLE_APPLICATION_CREDENTIALS_JSON (entire SA JSON contents, as string)
- GOOGLE_ANALYTICS_PROPERTY_ID (default: 531732958)
- KIT_API_KEY

Caches written to /tmp so the render step can pick them up:
- /tmp/dashboard_ga4_cache.json
- /tmp/kit_subscriber_cache.json

Then runs dashboard_render.py and writes to dashboard/index.html.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
DASHBOARD_DIR = REPO_ROOT / "dashboard"
STATE_DIR = REPO_ROOT / "state"
LOG = STATE_DIR / "dashboard_refresh_log.txt"

# dashboard_data.py reads caches from /home/user/workspace by default.
# Override via ARTEMIS_WORKSPACE so we can use /tmp in CI.
CACHE_DIR = Path(os.environ.get("ARTEMIS_WORKSPACE", "/tmp/artemis_cache"))
CACHE_DIR.mkdir(parents=True, exist_ok=True)

GA4_CACHE = CACHE_DIR / "dashboard_ga4_cache.json"
KIT_CACHE = CACHE_DIR / "kit_subscriber_cache.json"

GA4_PROPERTY = os.environ.get("GOOGLE_ANALYTICS_PROPERTY_ID", "531732958")


def log(line: str):
    STATE_DIR.mkdir(exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} | {line}\n")
    print(line, file=sys.stderr)


# ---------- GA4 ----------
def fetch_ga4():
    """Fetch 28-day daily user metrics from GA4 Data API."""
    from google.oauth2 import service_account
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Metric, RunReportRequest,
    )

    sa_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not sa_json:
        raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS_JSON env var missing")
    sa_info = json.loads(sa_json)
    creds = service_account.Credentials.from_service_account_info(sa_info)
    client = BetaAnalyticsDataClient(credentials=creds)

    req = RunReportRequest(
        property=f"properties/{GA4_PROPERTY}",
        date_ranges=[DateRange(start_date="28daysAgo", end_date="yesterday")],
        dimensions=[Dimension(name="date")],
        metrics=[
            Metric(name="activeUsers"),
            Metric(name="newUsers"),
            Metric(name="screenPageViews"),
            Metric(name="sessions"),
        ],
    )
    resp = client.run_report(req)
    rows = []
    for row in resp.rows:
        d = row.dimension_values[0].value  # YYYYMMDD
        m = [int(v.value) for v in row.metric_values]
        rows.append({
            "date": f"{d[:4]}-{d[4:6]}-{d[6:]}",
            "active": m[0],
            "new": m[1],
            "views": m[2],
            "sessions": m[3],
        })
    rows.sort(key=lambda r: r["date"])
    out = {
        "daily_users": rows,
        "total_active_28d": sum(r["active"] for r in rows),
        "total_new_28d": sum(r["new"] for r in rows),
        "total_sessions_28d": sum(r["sessions"] for r in rows),
        "total_views_28d": sum(r["views"] for r in rows),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    GA4_CACHE.write_text(json.dumps(out, indent=2))
    log(f"ga4 ok | 28d_active={out['total_active_28d']} latest={rows[-1] if rows else 'none'}")
    return out


# ---------- Kit ----------
def fetch_kit():
    api_key = os.environ.get("KIT_API_KEY")
    if not api_key:
        log("kit skipped | reason=no_KIT_API_KEY")
        return None

    headers = {"X-Kit-Api-Key": api_key}
    active = 0
    cursor = None
    while True:
        url = "https://api.kit.com/v4/subscribers?status=active&per_page=500"
        if cursor:
            url += f"&after={cursor}"
        req = urllib.request.Request(url, headers=headers)
        try:
            resp = urllib.request.urlopen(req, timeout=30)
        except urllib.error.HTTPError as e:
            body = e.read()[:300].decode("utf-8", "replace")
            log(f"kit error | status={e.code} | body={body}")
            return None
        d = json.loads(resp.read())
        active += len(d.get("subscribers", []))
        pag = d.get("pagination", {})
        if pag.get("has_next_page"):
            cursor = pag["end_cursor"]
        else:
            break

    req2 = urllib.request.Request(
        "https://api.kit.com/v4/broadcasts?per_page=10", headers=headers
    )
    try:
        d2 = json.loads(urllib.request.urlopen(req2, timeout=30).read())
        recent = [
            {"id": b.get("id"), "subject": b.get("subject"),
             "send_at": b.get("send_at"), "public": b.get("public")}
            for b in d2.get("broadcasts", [])[:10]
        ]
    except Exception as e:
        recent = []
        log(f"kit broadcasts fetch failed: {e}")

    out = {
        "active_subscribers": active,
        "recent_broadcasts": recent,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    KIT_CACHE.write_text(json.dumps(out, indent=2))
    log(f"kit ok | active_subscribers={active}")
    return out


# ---------- Render ----------
def render_dashboard():
    # Pass cache dir via env so dashboard_data.py reads from /tmp/artemis_cache
    env = os.environ.copy()
    env["ARTEMIS_WORKSPACE"] = str(CACHE_DIR)
    out = subprocess.check_output(
        [sys.executable, str(SCRIPTS / "dashboard_render.py")],
        cwd=str(REPO_ROOT),
        env=env,
    )
    log(f"render ok | html_bytes={len(out) if isinstance(out, bytes) else 'na'}")


def main():
    log("dashboard_refresh start")
    try:
        fetch_ga4()
    except Exception as e:
        log(f"ga4 FAILED: {type(e).__name__}: {e}")
        sys.exit(1)

    fetch_kit()  # soft-fails

    try:
        render_dashboard()
    except Exception as e:
        log(f"render FAILED: {type(e).__name__}: {e}")
        sys.exit(1)

    log("dashboard_refresh done")


if __name__ == "__main__":
    main()
