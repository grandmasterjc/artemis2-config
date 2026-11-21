#!/usr/bin/env python3
"""One-off, read-only diagnostic: push notification events per platform.

Answers one question: are iPhone users still opening push notifications
after the app moved to a new developer team on 1 Oct 2026? Prints tables
to the log. Writes nothing and sends nothing.
"""
import json
import os
import sys
from collections import defaultdict

from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Filter, FilterExpression, Metric, RunReportRequest,
)

PUSH_DAYS = {
    "20260924", "20260930", "20261008", "20261015", "20261023",
    "20261025", "20261111", "20261121",
}


def main():
    sa_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    prop = os.environ.get("GOOGLE_ANALYTICS_PROPERTY_ID", "531732958")
    if not sa_json:
        print("no GOOGLE_APPLICATION_CREDENTIALS_JSON", file=sys.stderr)
        sys.exit(1)
    creds = service_account.Credentials.from_service_account_info(json.loads(sa_json))
    client = BetaAnalyticsDataClient(credentials=creds)
    only_push = FilterExpression(filter=Filter(
        field_name="eventName",
        string_filter=Filter.StringFilter(
            match_type=Filter.StringFilter.MatchType.BEGINS_WITH, value="notification_"),
    ))

    # 1) Per day and platform.
    resp = client.run_report(RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date="2026-09-15", end_date="today")],
        dimensions=[Dimension(name="date"), Dimension(name="platform"), Dimension(name="eventName")],
        metrics=[Metric(name="eventCount")],
        dimension_filter=only_push,
        limit=10000,
    ))
    table = defaultdict(lambda: defaultdict(int))
    for r in resp.rows:
        d, plat, ev = (v.value for v in r.dimension_values)
        table[d][(plat, ev)] += int(r.metric_values[0].value)
    print("== notification events per day (push days marked *)")
    print("date      | iOS open | iOS fg | Android open | Android receive")
    for d in sorted(table):
        row = table[d]
        mark = "*" if d in PUSH_DAYS else " "
        print(f"{d}{mark} | {row[('iOS','notification_open')]:8d} | "
              f"{row[('iOS','notification_foreground')]:6d} | "
              f"{row[('Android','notification_open')]:12d} | "
              f"{row[('Android','notification_receive')]:15d}")

    # 2) iOS by app version since the transfer.
    resp = client.run_report(RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date="2026-10-01", end_date="today")],
        dimensions=[Dimension(name="platform"), Dimension(name="appVersion"), Dimension(name="eventName")],
        metrics=[Metric(name="eventCount")],
        dimension_filter=only_push,
        limit=10000,
    ))
    print("\n== since 2026-10-01, by platform and app version")
    for r in sorted(resp.rows, key=lambda r: [v.value for v in r.dimension_values]):
        plat, ver, ev = (v.value for v in r.dimension_values)
        print(f"{plat:8s} {ver:10s} {ev:26s} {r.metric_values[0].value}")

    # 3) Active users by platform and version, last 28 days, for scale.
    resp = client.run_report(RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date="28daysAgo", end_date="today")],
        dimensions=[Dimension(name="platform"), Dimension(name="appVersion")],
        metrics=[Metric(name="activeUsers")],
        limit=1000,
    ))
    print("\n== active users, last 28 days")
    for r in sorted(resp.rows, key=lambda r: [v.value for v in r.dimension_values]):
        plat, ver = (v.value for v in r.dimension_values)
        print(f"{plat:8s} {ver:10s} {r.metric_values[0].value}")


if __name__ == "__main__":
    main()
