#!/usr/bin/env python3
"""Backfill GA4 stats into state/push_history.csv.

For each push row aged between 24h and 14d, query GA4 for:
  - notification_open events tagged with that article_id
  - notification_foreground events
  - notification_toggled events
and update extra CSV columns (opens, unique_users, foreground, toggled, days_post_push, last_backfill_at).

GA4 queries go via the `external-tool` CLI (programmatic-tool-calling skill),
NOT the `functions` Python module. Caller must pass api_credentials=['external-tools'].

Writes /tmp/push_backfill_summary.json with shape:
  {
    "result": {
      "rows_backfilled": N,
      "rows_skipped": N,
      "notifications_to_send": [
        {"title": "...", "opens": N, "unique_users": N, "article_id": "...", "days_post_push": N}
      ]
    }
  }
or, on fatal error:
  {"error": "..."}
"""
from __future__ import annotations
import csv
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = REPO_ROOT / "state"
PUSH_HISTORY = STATE_DIR / "push_history.csv"
LOG = STATE_DIR / "push_backfill_log.txt"
SUMMARY_OUT = Path("/tmp/push_backfill_summary.json")
GA4_PROPERTY = "531732958"

FIELDS = [
    "timestamp_utc", "title", "body", "article_id", "topic", "message_id",
    "opens", "unique_users", "foreground", "toggled", "days_post_push", "last_backfill_at",
]


def log(line: str):
    STATE_DIR.mkdir(exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} | {line}\n")


def write_summary(payload: dict):
    SUMMARY_OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def read_rows() -> list[dict]:
    if not PUSH_HISTORY.exists():
        return []
    rows = []
    with PUSH_HISTORY.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            for k in FIELDS:
                r.setdefault(k, "")
            rows.append(r)
    return rows


def write_rows(rows: list[dict]):
    with PUSH_HISTORY.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def ga4_query(article_id: str, start_date: str, end_date: str) -> dict:
    """Run a GA4 report via the external-tool CLI. Returns aggregated counts."""
    payload = {
        "property": f"properties/{GA4_PROPERTY}",
        "dateRanges": [{"startDate": start_date, "endDate": end_date}],
        "dimensions": [{"name": "eventName"}],
        "metrics": [{"name": "eventCount"}, {"name": "totalUsers"}],
        "dimensionFilter": {
            "andGroup": {
                "expressions": [
                    {"filter": {"fieldName": "eventName", "stringFilter": {"matchType": "BEGINS_WITH", "value": "notification_"}}},
                    {"filter": {"fieldName": "customEvent:article_id", "stringFilter": {"value": article_id}}},
                ]
            }
        },
    }
    cmd = [
        "external-tool", "call",
        "--source-id", "google_analytics__pipedream",
        "--tool", "google_analytics-run-report-in-ga4",
        "--input", json.dumps(payload),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        raise RuntimeError("external-tool CLI not found on PATH")
    if r.returncode != 0:
        raise RuntimeError(f"GA4 query failed: {r.stderr.strip()}")
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"GA4 returned non-JSON: {r.stdout[:200]}")


def aggregate(ga4_response: dict) -> dict:
    opens = 0
    unique_users = 0
    foreground = 0
    toggled = 0
    for row in (ga4_response.get("rows") or []):
        name = row["dimensionValues"][0]["value"]
        count = int(row["metricValues"][0]["value"])
        users = int(row["metricValues"][1]["value"])
        if name == "notification_open":
            opens += count
            unique_users = max(unique_users, users)
        elif name == "notification_foreground":
            foreground += count
        elif name == "notification_toggled":
            toggled += count
    return {"opens": opens, "unique_users": unique_users, "foreground": foreground, "toggled": toggled}


def main():
    try:
        rows = read_rows()
        now = datetime.now(timezone.utc)
        rows_backfilled = 0
        rows_skipped = 0
        notifications = []

        for row in rows:
            try:
                pushed_at = datetime.fromisoformat(row["timestamp_utc"])
            except Exception:
                rows_skipped += 1
                continue
            age = now - pushed_at
            if age < timedelta(hours=24) or age > timedelta(days=14):
                rows_skipped += 1
                continue
            if not row.get("article_id"):
                rows_skipped += 1
                continue

            start = pushed_at.date().isoformat()
            end = now.date().isoformat()
            try:
                resp = ga4_query(row["article_id"], start, end)
            except Exception as e:
                log(f"ga4_error | article={row['article_id']} | {e}")
                rows_skipped += 1
                continue

            agg = aggregate(resp)
            row.update({
                "opens": str(agg["opens"]),
                "unique_users": str(agg["unique_users"]),
                "foreground": str(agg["foreground"]),
                "toggled": str(agg["toggled"]),
                "days_post_push": str(age.days),
                "last_backfill_at": now.isoformat(),
            })
            rows_backfilled += 1
            if agg["opens"] >= 100:
                notifications.append({
                    "title": row.get("title", ""),
                    "opens": agg["opens"],
                    "unique_users": agg["unique_users"],
                    "article_id": row["article_id"],
                    "days_post_push": age.days,
                })

        write_rows(rows)
        log(f"ok | backfilled={rows_backfilled} | skipped={rows_skipped}")
        write_summary({"result": {
            "rows_backfilled": rows_backfilled,
            "rows_skipped": rows_skipped,
            "notifications_to_send": notifications,
        }})
    except Exception as e:
        log(f"fatal | {type(e).__name__}: {e}")
        write_summary({"error": f"{type(e).__name__}: {e}"})
        sys.exit(1)


if __name__ == "__main__":
    main()
