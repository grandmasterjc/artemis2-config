#!/usr/bin/env python3
"""One-off, read-only diagnostic: do NEW iPhone installs get push?

Splits notification_open by when the user first opened the app, so we can
see whether devices that installed after the 1 Oct 2026 team change ever
open a push. Prints tables to the log. Writes nothing and sends nothing.
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


def bucket(first):
    if first < "20260801":
        return "before Aug"
    return first[:6]  # YYYYMM


def main():
    sa_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    prop = os.environ.get("GOOGLE_ANALYTICS_PROPERTY_ID", "531732958")
    if not sa_json:
        print("no GOOGLE_APPLICATION_CREDENTIALS_JSON", file=sys.stderr)
        sys.exit(1)
    creds = service_account.Credentials.from_service_account_info(json.loads(sa_json))
    client = BetaAnalyticsDataClient(credentials=creds)

    def event_filter(name):
        return FilterExpression(filter=Filter(
            field_name="eventName",
            string_filter=Filter.StringFilter(value=name),
        ))

    windows = [
        ("Aug 20 to Sep 30 (old team)", "2026-08-20", "2026-09-30"),
        ("Oct 8 to today (new team)", "2026-10-08", "today"),
    ]
    for label, start, end in windows:
        print(f"\n== {label}: notification_open by first-session month")
        resp = client.run_report(RunReportRequest(
            property=f"properties/{prop}",
            date_ranges=[DateRange(start_date=start, end_date=end)],
            dimensions=[Dimension(name="platform"), Dimension(name="firstSessionDate")],
            metrics=[Metric(name="eventCount"), Metric(name="totalUsers")],
            dimension_filter=event_filter("notification_open"),
            limit=20000,
        ))
        agg = defaultdict(lambda: [0, 0])
        for r in resp.rows:
            plat, first = (v.value for v in r.dimension_values)
            key = (plat, bucket(first))
            agg[key][0] += int(r.metric_values[0].value)
            agg[key][1] += int(r.metric_values[1].value)
        print("platform  first session  opens  users")
        for key in sorted(agg):
            print(f"{key[0]:8s}  {key[1]:13s}  {agg[key][0]:5d}  {agg[key][1]:5d}")

    # New users per month and platform, for scale.
    print("\n== new users per month")
    resp = client.run_report(RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date="2026-08-01", end_date="today")],
        dimensions=[Dimension(name="platform"), Dimension(name="yearMonth")],
        metrics=[Metric(name="newUsers")],
        limit=1000,
    ))
    for r in sorted(resp.rows, key=lambda r: [v.value for v in r.dimension_values]):
        plat, ym = (v.value for v in r.dimension_values)
        print(f"{plat:8s}  {ym}  {r.metric_values[0].value}")

    # iOS opens by first-session DATE in the new-team window, newest cohorts.
    print("\n== iOS, Oct 8 to today: opens from users first seen on or after 2026-10-01")
    resp = client.run_report(RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date="2026-10-08", end_date="today")],
        dimensions=[Dimension(name="platform"), Dimension(name="firstSessionDate"),
                    Dimension(name="appVersion")],
        metrics=[Metric(name="eventCount")],
        dimension_filter=event_filter("notification_open"),
        limit=20000,
    ))
    rows = []
    for r in resp.rows:
        plat, first, ver = (v.value for v in r.dimension_values)
        if plat == "iOS" and first >= "20261001":
            rows.append((first, ver, int(r.metric_values[0].value)))
    for first, ver, n in sorted(rows):
        print(f"first session {first}  version {ver:8s}  opens {n}")
    if not rows:
        print("none")

    # Today so far.
    print("\n== today so far, notification events")
    resp = client.run_report(RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date="today", end_date="today")],
        dimensions=[Dimension(name="platform"), Dimension(name="eventName")],
        metrics=[Metric(name="eventCount")],
        limit=1000,
    ))
    seen = False
    for r in sorted(resp.rows, key=lambda r: [v.value for v in r.dimension_values]):
        plat, ev = (v.value for v in r.dimension_values)
        if ev.startswith("notification_"):
            seen = True
            print(f"{plat:8s}  {ev:26s}  {r.metric_values[0].value}")
    if not seen:
        print("no notification events processed yet")


if __name__ == "__main__":
    main()
