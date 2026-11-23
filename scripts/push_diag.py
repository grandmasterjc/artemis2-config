#!/usr/bin/env python3
"""Read-only report: how many iPhone users open each article alert?

Used to measure the effect of app 2.5.4 (released 23 Nov 2026), which
signs phones up for alerts again after a restore from backup. Prints
tables to the log. Writes nothing and sends nothing.

Push days come from state/push_history.csv on main, so a new alert shows
up here without changing this script.
"""
import csv
import io
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

import requests
from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Filter, FilterExpression, Metric, RunReportRequest,
)

PUSH_LOG = "https://raw.githubusercontent.com/grandmasterjc/artemis2-config/main/state/push_history.csv"


def push_days():
    """{YYYYMMDD: article_id} for every alert in the push log (UTC dates)."""
    days = {}
    try:
        text = requests.get(PUSH_LOG, timeout=30).text
        for row in csv.DictReader(io.StringIO(text)):
            stamp = (row.get("timestamp_utc") or "")[:10].replace("-", "")
            if len(stamp) == 8:
                days[stamp] = row.get("article_id", "")
    except Exception as e:  # the report still works without the marks
        print(f"could not read the push log: {e}")
    return days


def main():
    sa_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    prop = os.environ.get("GOOGLE_ANALYTICS_PROPERTY_ID", "531732958")
    if not sa_json:
        print("no GOOGLE_APPLICATION_CREDENTIALS_JSON", file=sys.stderr)
        sys.exit(1)
    creds = service_account.Credentials.from_service_account_info(json.loads(sa_json))
    client = BetaAnalyticsDataClient(credentials=creds)
    pushes = push_days()

    def event_filter(name, begins=False):
        match = (Filter.StringFilter.MatchType.BEGINS_WITH if begins
                 else Filter.StringFilter.MatchType.EXACT)
        return FilterExpression(filter=Filter(
            field_name="eventName",
            string_filter=Filter.StringFilter(match_type=match, value=name),
        ))

    # 1) Per alert: iPhone opens on the push day and the day after.
    resp = client.run_report(RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date="2026-09-15", end_date="today")],
        dimensions=[Dimension(name="date"), Dimension(name="platform"), Dimension(name="eventName")],
        metrics=[Metric(name="eventCount")],
        dimension_filter=event_filter("notification_", begins=True),
        limit=20000,
    ))
    table = defaultdict(lambda: defaultdict(int))
    for r in resp.rows:
        d, plat, ev = (v.value for v in r.dimension_values)
        table[d][(plat, ev)] += int(r.metric_values[0].value)

    def next_day(d):
        return (datetime.strptime(d, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")

    print("== per alert: opens on the push day plus the day after")
    print("push day  | iPhone opens | Android opens | Android received | article")
    for d in sorted(pushes):
        if d < "20260915":
            continue
        n = next_day(d)
        ios = table[d][("iOS", "notification_open")] + table[n][("iOS", "notification_open")]
        a_open = table[d][("Android", "notification_open")] + table[n][("Android", "notification_open")]
        a_recv = table[d][("Android", "notification_receive")] + table[n][("Android", "notification_receive")]
        print(f"{d}  | {ios:12d} | {a_open:13d} | {a_recv:16d} | {pushes[d]}")

    # 2) iPhone opens by app version for the three latest alerts.
    resp = client.run_report(RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date="45daysAgo", end_date="today")],
        dimensions=[Dimension(name="date"), Dimension(name="platform"), Dimension(name="appVersion")],
        metrics=[Metric(name="eventCount")],
        dimension_filter=event_filter("notification_open"),
        limit=20000,
    ))
    by_version = defaultdict(lambda: defaultdict(int))
    for r in resp.rows:
        d, plat, ver = (v.value for v in r.dimension_values)
        if plat == "iOS":
            by_version[d][ver] += int(r.metric_values[0].value)
    print("\n== iPhone opens by app version, three latest alerts (push day plus the day after)")
    for d in sorted(pushes)[-3:]:
        n = next_day(d)
        merged = defaultdict(int)
        for day in (d, n):
            for ver, count in by_version[day].items():
                merged[ver] += count
        parts = ", ".join(f"{ver}: {merged[ver]}" for ver in sorted(merged)) or "none yet"
        print(f"{d}  {parts}")

    # 3) How far 2.5.4 has spread.
    resp = client.run_report(RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date="7daysAgo", end_date="today")],
        dimensions=[Dimension(name="platform"), Dimension(name="appVersion")],
        metrics=[Metric(name="activeUsers")],
        limit=1000,
    ))
    print("\n== iPhone active users by app version, last 7 days")
    for r in sorted(resp.rows, key=lambda r: [v.value for v in r.dimension_values]):
        plat, ver = (v.value for v in r.dimension_values)
        if plat == "iOS":
            print(f"{ver:10s} {r.metric_values[0].value}")

    # 4) Today so far, in case the alert went out today.
    today = datetime.utcnow().strftime("%Y%m%d")
    print(f"\n== today so far ({today}, still being processed)")
    row = table.get(today, {})
    print(f"iPhone opens: {row.get(('iOS', 'notification_open'), 0)}, "
          f"Android received: {row.get(('Android', 'notification_receive'), 0)}")


if __name__ == "__main__":
    main()
