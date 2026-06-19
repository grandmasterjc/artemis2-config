"""
Dashboard data sources for Artemis Tracker.

Each function returns a dict; missing credentials soft-fail with status='skipped'
so the dashboard always renders even if one source is down.

Sources:
- GA4 (analytics, DAU, retention)
- Kit (newsletter subscribers, broadcasts)
- App Store Connect API (downloads, ratings, reviews)
- Bluesky (followers, posts, engagement)
- Mastodon (followers, posts, engagement)
- Roadmap (ROADMAP.md file)
- Strategy targets (STRATEGY.md hardcoded for now)
"""

from __future__ import annotations

import base64
import csv
import io
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _http_get(url: str, headers: dict | None = None, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def _http_get_bytes(url: str, headers: dict | None = None, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# ---------- GA4 ----------
def fetch_ga4() -> dict:
    sa_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    prop = os.environ.get("GOOGLE_ANALYTICS_PROPERTY_ID", "531732958")
    if not sa_json:
        return {"status": "skipped", "reason": "no GOOGLE_APPLICATION_CREDENTIALS_JSON"}
    try:
        from google.oauth2 import service_account
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange, Dimension, Metric, RunReportRequest,
        )
        sa_info = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(sa_info)
        client = BetaAnalyticsDataClient(credentials=creds)

        # Daily users — 90d so we can chart trajectory toward Aug 31
        req = RunReportRequest(
            property=f"properties/{prop}",
            date_ranges=[DateRange(start_date="90daysAgo", end_date="yesterday")],
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
            d = row.dimension_values[0].value
            m = [int(v.value) for v in row.metric_values]
            rows.append({
                "date": f"{d[:4]}-{d[4:6]}-{d[6:]}",
                "active": m[0], "new": m[1], "views": m[2], "sessions": m[3],
            })
        rows.sort(key=lambda r: r["date"])

        # Top countries 30d
        try:
            req_c = RunReportRequest(
                property=f"properties/{prop}",
                date_ranges=[DateRange(start_date="30daysAgo", end_date="yesterday")],
                dimensions=[Dimension(name="country")],
                metrics=[Metric(name="activeUsers")],
                limit=10,
            )
            resp_c = client.run_report(req_c)
            countries = [
                {"country": r.dimension_values[0].value,
                 "active": int(r.metric_values[0].value)}
                for r in resp_c.rows
            ]
        except Exception:
            countries = []

        last28 = rows[-28:] if len(rows) >= 28 else rows
        last7 = rows[-7:] if len(rows) >= 7 else rows
        latest = rows[-1] if rows else None

        # Push notification event counts (30d) -- requires Firebase to GA4 export.
        push_events_30d = {}
        try:
            req_p = RunReportRequest(
                property=f"properties/{prop}",
                date_ranges=[DateRange(start_date="30daysAgo", end_date="yesterday")],
                dimensions=[Dimension(name="eventName")],
                metrics=[Metric(name="eventCount")],
            )
            resp_p = client.run_report(req_p)
            for r in resp_p.rows:
                name = r.dimension_values[0].value
                if name.startswith("notification_"):
                    push_events_30d[name] = int(r.metric_values[0].value)
        except Exception:
            push_events_30d = {}

        # iOS Firebase reliably logs notification_open (user tapped from outside
        # app) and notification_foreground (user was in app when push arrived).
        # notification_receive is rarely logged. Approximate open rate as:
        # opens / (opens + foreground) -- share of pushes user actively engaged
        # with vs. pushes that arrived while app was already in view.
        push_opened = push_events_30d.get("notification_open", 0)
        push_foreground = push_events_30d.get("notification_foreground", 0)
        push_open_rate = None
        denom = push_opened + push_foreground
        if denom > 0:
            push_open_rate = round(push_opened / denom, 4)

        return {
            "status": "ok",
            "daily_users": rows,  # 90 days
            "latest": latest,
            "total_active_28d": sum(r["active"] for r in last28),
            "total_new_28d": sum(r["new"] for r in last28),
            "total_sessions_28d": sum(r["sessions"] for r in last28),
            "total_views_28d": sum(r["views"] for r in last28),
            "avg_dau_7d": round(sum(r["active"] for r in last7) / max(len(last7), 1), 1),
            "avg_dau_28d": round(sum(r["active"] for r in last28) / max(len(last28), 1), 1),
            "top_countries_30d": countries,
            "push_events_30d": push_events_30d,
            "push_open_rate_30d": push_open_rate,
            "fetched_at": _now_iso(),
        }
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


# ---------- Kit ----------
def fetch_kit() -> dict:
    api_key = os.environ.get("KIT_API_KEY")
    if not api_key:
        return {"status": "skipped", "reason": "no KIT_API_KEY"}
    headers = {"X-Kit-Api-Key": api_key}
    try:
        active = 0
        cursor = None
        while True:
            url = "https://api.kit.com/v4/subscribers?status=active&per_page=500"
            if cursor:
                url += f"&after={cursor}"
            d = _http_get(url, headers)
            active += len(d.get("subscribers", []))
            pag = d.get("pagination", {})
            if pag.get("has_next_page"):
                cursor = pag["end_cursor"]
            else:
                break

        # inactive count
        inactive = 0
        try:
            d_in = _http_get(
                "https://api.kit.com/v4/subscribers?status=inactive&per_page=500",
                headers,
            )
            inactive = len(d_in.get("subscribers", []))
        except Exception:
            pass

        # broadcasts
        try:
            d2 = _http_get("https://api.kit.com/v4/broadcasts?per_page=10", headers)
            recent = [
                {
                    "id": b.get("id"),
                    "subject": b.get("subject"),
                    "send_at": b.get("send_at"),
                    "public": b.get("public"),
                }
                for b in d2.get("broadcasts", [])[:10]
            ]
        except Exception:
            recent = []

        return {
            "status": "ok",
            "active_subscribers": active,
            "inactive_subscribers": inactive,
            "recent_broadcasts": recent,
            "fetched_at": _now_iso(),
        }
    except urllib.error.HTTPError as e:
        return {"status": "error", "error": f"HTTP {e.code}", "body": e.read()[:200].decode("utf-8", "replace")}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


# ---------- App Store Connect ----------
def _asc_jwt(key_id: str, issuer_id: str, private_key_pem: str) -> str:
    """Build a JWT for App Store Connect API."""
    try:
        import jwt  # PyJWT
    except ImportError:
        raise RuntimeError("PyJWT not installed")

    now = int(time.time())
    payload = {
        "iss": issuer_id,
        "iat": now,
        "exp": now + 20 * 60,  # 20 min max
        "aud": "appstoreconnect-v1",
    }
    headers = {"kid": key_id, "typ": "JWT"}
    return jwt.encode(payload, private_key_pem, algorithm="ES256", headers=headers)


def _fetch_asc_daily_sales(token: str, vendor_number: str, report_date: str) -> list[dict]:
    """Fetch one DAILY SALES SUMMARY report. Returns list of row dicts.

    Apple gates the API on vendor_number. Reports are gzipped TSV with a 1-2 day lag.
    Returns [] on missing data (404), API error, or empty response.
    """
    import gzip
    url = (
        "https://api.appstoreconnect.apple.com/v1/salesReports"
        f"?filter%5Bfrequency%5D=DAILY"
        f"&filter%5BreportType%5D=SALES"
        f"&filter%5BreportSubType%5D=SUMMARY"
        f"&filter%5BvendorNumber%5D={vendor_number}"
        f"&filter%5BreportDate%5D={report_date}"
        f"&filter%5Bversion%5D=1_1"
    )
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/a-gzip, application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
    except urllib.error.HTTPError:
        return []
    except Exception:
        return []
    try:
        text = gzip.decompress(raw).decode("utf-8")
    except Exception:
        return []
    lines = text.splitlines()
    if len(lines) < 2:
        return []
    header = lines[0].split("\t")
    out = []
    for line in lines[1:]:
        cells = line.split("\t")
        if len(cells) == len(header):
            out.append(dict(zip(header, cells)))
    return out


def _fetch_asc_subscription_status(token: str, vendor_number: str, app_apple_id: str, report_date: str) -> list[dict]:
    """Fetch one DAILY SUBSCRIPTION status report. Returns active subscriber counts per SKU.

    Returns rows with columns including App Apple ID, Subscription Name,
    Subscription Apple ID, Standard Subscription Duration, Customer Price,
    Customer Currency, Country Code, Promotional Offer Name, Promotional Offer ID,
    Subscription Offer Type, Subscription Offer Duration, Active Standard Price
    Subscriptions, Active Free Trial Introductory Offer Subscriptions, etc.
    """
    import gzip
    url = (
        "https://api.appstoreconnect.apple.com/v1/salesReports"
        f"?filter%5Bfrequency%5D=DAILY"
        f"&filter%5BreportType%5D=SUBSCRIPTION"
        f"&filter%5BreportSubType%5D=SUMMARY"
        f"&filter%5BvendorNumber%5D={vendor_number}"
        f"&filter%5BreportDate%5D={report_date}"
        f"&filter%5Bversion%5D=1_3"
    )
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/a-gzip, application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
    except urllib.error.HTTPError:
        return []
    except Exception:
        return []
    try:
        text = gzip.decompress(raw).decode("utf-8")
    except Exception:
        return []
    lines = text.splitlines()
    if len(lines) < 2:
        return []
    header = lines[0].split("\t")
    out = []
    for line in lines[1:]:
        cells = line.split("\t")
        if len(cells) == len(header):
            row = dict(zip(header, cells))
            if app_apple_id and row.get("App Apple ID", "").strip() != app_apple_id:
                continue
            out.append(row)
    return out


def _fetch_asc_subscription_event(token: str, vendor_number: str, app_apple_id: str, report_date: str) -> list[dict]:
    """Fetch one DAILY SUBSCRIPTION_EVENT report.

    Each row is a subscription event on that day with columns including
    Event, Subscription Apple ID, Subscription Name, Standard Subscription Duration,
    Customer Price, Country Code, App Apple ID, Days Before Canceling,
    Cancellation Reason. Event values include: Subscribe, Cancel, Refund,
    Renew, Renewal, Reactivate, etc.
    """
    import gzip
    url = (
        "https://api.appstoreconnect.apple.com/v1/salesReports"
        f"?filter%5Bfrequency%5D=DAILY"
        f"&filter%5BreportType%5D=SUBSCRIPTION_EVENT"
        f"&filter%5BreportSubType%5D=SUMMARY"
        f"&filter%5BvendorNumber%5D={vendor_number}"
        f"&filter%5BreportDate%5D={report_date}"
        f"&filter%5Bversion%5D=1_3"
    )
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/a-gzip, application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
    except urllib.error.HTTPError:
        return []
    except Exception:
        return []
    try:
        text = gzip.decompress(raw).decode("utf-8")
    except Exception:
        return []
    lines = text.splitlines()
    if len(lines) < 2:
        return []
    header = lines[0].split("\t")
    out = []
    for line in lines[1:]:
        cells = line.split("\t")
        if len(cells) == len(header):
            row = dict(zip(header, cells))
            if app_apple_id and row.get("App Apple ID", "").strip() != app_apple_id:
                continue
            out.append(row)
    return out


def _summarize_asc_subscription_status(rows: list[dict]) -> dict:
    """Aggregate active subscriber counts and compute ARR/MRR.

    Each row represents a (sku, country, offer) bucket on a given day. We sum
    the active-subscription columns across all rows. ARR is computed using
    each row's Customer Price + duration + Apple's proceeds factor (85% under
    Small Business Program; override with APPLE_PROCEEDS_FACTOR env var).
    Free-trial subscriptions count toward active_total but contribute zero ARR.
    Prices in non-USD currencies are converted with static FX rates (override
    via FX_RATES env var as JSON like {"EUR":1.07,"GBP":1.26}).
    """
    if not rows:
        return {"active_total": 0, "by_product": {}, "by_country": [], "arr_usd": 0.0, "mrr_usd": 0.0}

    try:
        proceeds_factor = float(os.environ.get("APPLE_PROCEEDS_FACTOR", "0.85"))
    except ValueError:
        proceeds_factor = 0.85

    default_fx = {
        "USD": 1.0, "EUR": 1.07, "GBP": 1.26, "CAD": 0.73, "AUD": 0.66,
        "NOK": 0.094, "SEK": 0.094, "DKK": 0.144, "CHF": 1.13, "JPY": 0.0064,
        "INR": 0.012, "BRL": 0.18, "MXN": 0.054, "PLN": 0.25, "CZK": 0.043,
        "TRY": 0.029, "ZAR": 0.054, "CNY": 0.14, "KRW": 0.00072, "SGD": 0.74,
        "HKD": 0.128, "NZD": 0.60, "RUB": 0.011, "ILS": 0.27, "AED": 0.272,
    }
    try:
        fx_override = json.loads(os.environ.get("FX_RATES", "{}"))
        default_fx.update(fx_override)
    except (json.JSONDecodeError, TypeError):
        pass

    by_product: dict = {}
    by_country: dict = {}
    active_total = 0
    arr_usd = 0.0

    cols = [
        "Active Standard Price Subscriptions",
        "Active Free Trial Introductory Offer Subscriptions",
        "Active Pay Up Front Introductory Offer Subscriptions",
        "Active Pay As You Go Introductory Offer Subscriptions",
        "Active Promotional Offer Subscriptions",
        "Active Win-Back Offer Subscriptions",
    ]

    for r in rows:
        sku = (r.get("Subscription Name") or r.get("Subscription Apple ID") or "unknown").strip()
        country = (r.get("Country Code") or "??").strip()
        duration = (r.get("Standard Subscription Duration") or "").strip().lower()

        try:
            paying = int(r.get("Active Standard Price Subscriptions", "0") or 0)
            paying += int(r.get("Active Promotional Offer Subscriptions", "0") or 0)
            paying += int(r.get("Active Win-Back Offer Subscriptions", "0") or 0)
            paying += int(r.get("Active Pay Up Front Introductory Offer Subscriptions", "0") or 0)
            paying += int(r.get("Active Pay As You Go Introductory Offer Subscriptions", "0") or 0)
        except ValueError:
            paying = 0

        row_total = 0
        for col in cols:
            v = r.get(col, "0")
            try:
                row_total += int(v) if v else 0
            except ValueError:
                pass
        if row_total <= 0:
            continue
        active_total += row_total
        by_product[sku] = by_product.get(sku, 0) + row_total
        by_country[country] = by_country.get(country, 0) + row_total

        try:
            price = float(r.get("Customer Price", "0") or 0)
        except ValueError:
            price = 0.0
        currency = (r.get("Customer Currency") or "USD").strip()
        price_usd = price * default_fx.get(currency, 1.0)

        if "year" in duration:
            annual_per_sub = price_usd
        elif "6 month" in duration:
            annual_per_sub = price_usd * 2
        elif "3 month" in duration:
            annual_per_sub = price_usd * 4
        elif "month" in duration:
            annual_per_sub = price_usd * 12
        elif "week" in duration:
            annual_per_sub = price_usd * 52
        else:
            annual_per_sub = price_usd * 12

        arr_usd += paying * annual_per_sub * proceeds_factor

    return {
        "active_total": active_total,
        "by_product": by_product,
        "by_country": sorted([{"country": k, "active": v} for k, v in by_country.items()], key=lambda x: x["active"], reverse=True),
        "arr_usd": round(arr_usd, 2),
        "mrr_usd": round(arr_usd / 12, 2),
        "proceeds_factor": proceeds_factor,
    }


def _summarize_asc_sales(rows: list[dict], bundle_prefix: str) -> dict:
    """Aggregate sales rows for one app (filtered by SKU prefix)."""
    from collections import defaultdict
    by_product = defaultdict(lambda: {"units": 0, "proceeds_usd": 0.0, "name": ""})
    by_day_sku = defaultdict(lambda: defaultdict(int))
    by_day_proceeds = defaultdict(float)
    by_country = defaultdict(lambda: {"units": 0, "proceeds_usd": 0.0})
    by_order_type = defaultdict(int)
    new_subs = 0
    new_installs = 0
    total_units = 0
    total_proceeds = 0.0

    # First-time download Product Type Identifiers across platforms:
    # 1, 1F = iPhone first download (free/paid)
    # 1T = Apple TV, 1E = Mac, F1 = iPad, FI = Universal, 1EP = Mac iOS-ported
    install_type_codes = {"1", "1F", "1T", "1E", "F1", "FI", "1EP"}

    for row in rows:
        sku = row.get("SKU", "")
        ptype = (row.get("Product Type Identifier", "") or "").strip()
        try:
            row_units = int(row.get("Units", "0") or 0)
        except ValueError:
            row_units = 0
        # Installs: SKU is the app SKU (e.g. 'artemisii-tracker-v1'),
        # not the subscription product id.
        if ptype in install_type_codes and "artemisii-tracker" in sku.lower():
            new_installs += row_units
        if bundle_prefix not in sku:
            continue
        try:
            units = int(row.get("Units", "0") or 0)
        except ValueError:
            units = 0
        try:
            proceeds_per_unit = float(row.get("Developer Proceeds", "0") or 0)
        except ValueError:
            proceeds_per_unit = 0.0
        proceeds_total = units * proceeds_per_unit
        product = by_product[sku]
        product["units"] += units
        product["proceeds_usd"] += proceeds_total
        product["name"] = row.get("Title", "") or product["name"]

        d = row.get("_report_date", "")
        if d:
            if "monthly" in sku:
                by_day_sku[d]["monthly"] += units
            elif "yearly" in sku:
                by_day_sku[d]["yearly"] += units
            else:
                by_day_sku[d]["other"] += units
            by_day_proceeds[d] += proceeds_total

        cc = row.get("Country Code", "") or ""
        if cc:
            by_country[cc]["units"] += units
            by_country[cc]["proceeds_usd"] += proceeds_total

        order_type = row.get("Order Type", "").strip() or "Standard"
        by_order_type[order_type] += units

        if row.get("Subscription", "").strip() == "New":
            new_subs += units

        total_units += units
        total_proceeds += proceeds_total

    by_day_list = []
    for d in sorted(by_day_sku.keys()):
        by_day_list.append({
            "date": d,
            "monthly": by_day_sku[d].get("monthly", 0),
            "yearly": by_day_sku[d].get("yearly", 0),
            "other": by_day_sku[d].get("other", 0),
            "proceeds_usd": round(by_day_proceeds[d], 2),
        })

    by_country_list = sorted(
        [{"country": cc, "units": v["units"], "proceeds_usd": round(v["proceeds_usd"], 2)}
         for cc, v in by_country.items()],
        key=lambda x: -x["units"],
    )

    by_product_out = {
        sku: {"units": v["units"], "proceeds_usd": round(v["proceeds_usd"], 2), "name": v["name"]}
        for sku, v in by_product.items()
    }

    return {
        "by_product": by_product_out,
        "by_day": by_day_list,
        "by_country": by_country_list,
        "by_order_type": dict(by_order_type),
        "total_units_30d": total_units,
        "total_proceeds_usd_30d": round(total_proceeds, 2),
        "new_subscribers_30d": new_subs,
        "new_installs_30d": new_installs,
    }


def fetch_app_store_connect() -> dict:
    key_id = os.environ.get("APP_STORE_CONNECT_KEY_ID")
    issuer_id = os.environ.get("APP_STORE_CONNECT_ISSUER_ID")
    private_key = os.environ.get("APP_STORE_CONNECT_PRIVATE_KEY")
    vendor_number = os.environ.get("APP_STORE_CONNECT_VENDOR_NUMBER")
    bundle_prefix = os.environ.get(
        "APP_STORE_CONNECT_BUNDLE_PREFIX", "no.bitfactory.artemisii.tracker"
    )
    if not (key_id and issuer_id and private_key):
        return {"status": "skipped", "reason": "ASC credentials missing"}

    try:
        token = _asc_jwt(key_id, issuer_id, private_key)
        headers = {"Authorization": f"Bearer {token}"}

        # Get apps list — find Artemis Tracker
        apps = _http_get(
            "https://api.appstoreconnect.apple.com/v1/apps?limit=20",
            headers,
        )
        artemis_app = None
        for a in apps.get("data", []):
            name = a.get("attributes", {}).get("name", "")
            if "artemis" in name.lower():
                artemis_app = a
                break
        if not artemis_app:
            return {"status": "error", "error": "Artemis app not found in ASC"}

        app_id = artemis_app["id"]
        app_name = artemis_app["attributes"].get("name")
        bundle_id = artemis_app["attributes"].get("bundleId")

        # Customer reviews — paginate to fetch up to 200
        reviews = []
        next_url = (
            f"https://api.appstoreconnect.apple.com/v1/apps/{app_id}/customerReviews"
            "?limit=200&sort=-createdDate"
        )
        pages = 0
        while next_url and pages < 4:
            try:
                page = _http_get(next_url, headers)
            except Exception:
                break
            for r in page.get("data", []):
                attr = r.get("attributes", {})
                reviews.append({
                    "id": r.get("id"),
                    "rating": int(attr.get("rating", 0)),
                    "title": (attr.get("title", "") or "")[:200],
                    "body": (attr.get("body", "") or "")[:400],
                    "reviewer": attr.get("reviewerNickname", "") or "",
                    "territory": attr.get("territory", "") or "",
                    "created": attr.get("createdDate", "") or "",
                })
            next_url = page.get("links", {}).get("next")
            pages += 1

        # Merge with persistent history CSV — dedup by review id
        hist_path = REPO_ROOT / "state" / "asc_reviews_history.csv"
        history = {}
        if hist_path.exists():
            try:
                import csv as _csv
                with hist_path.open() as f:
                    for row in _csv.DictReader(f):
                        if row.get("id"):
                            history[row["id"]] = row
            except Exception:
                history = {}

        new_count = 0
        for r in reviews:
            if r["id"] and r["id"] not in history:
                history[r["id"]] = {
                    "id": r["id"],
                    "rating": str(r["rating"]),
                    "created": r["created"],
                    "territory": r["territory"],
                    "reviewer": r["reviewer"],
                    "title": r["title"],
                    "body": r["body"],
                }
                new_count += 1

        # Write back history
        try:
            import csv as _csv
            hist_path.parent.mkdir(parents=True, exist_ok=True)
            with hist_path.open("w", newline="") as f:
                w = _csv.DictWriter(
                    f,
                    fieldnames=["id", "rating", "created", "territory", "reviewer", "title", "body"],
                )
                w.writeheader()
                for row in sorted(history.values(), key=lambda x: x.get("created", ""), reverse=True):
                    w.writerow(row)
        except Exception:
            pass

        # Compute rolling stats from full history
        now = datetime.now(timezone.utc)
        all_reviews = list(history.values())

        def _parse_dt(s):
            try:
                return datetime.fromisoformat(s.replace("Z", "+00:00"))
            except Exception:
                return None

        def _stats(items):
            ratings = [int(r["rating"]) for r in items if r.get("rating")]
            if not ratings:
                return {"count": 0, "avg": None, "share_4plus": None,
                        "dist": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}}
            dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for r in ratings:
                if r in dist:
                    dist[r] += 1
            avg = round(sum(ratings) / len(ratings), 2)
            share = round(100 * (dist[4] + dist[5]) / len(ratings), 1)
            return {"count": len(ratings), "avg": avg, "share_4plus": share, "dist": dist}

        cutoff_30d = now - timedelta(days=30)
        cutoff_90d = now - timedelta(days=90)
        last_30d = [r for r in all_reviews if (_parse_dt(r.get("created", "")) or now) >= cutoff_30d]
        last_90d = [r for r in all_reviews if (_parse_dt(r.get("created", "")) or now) >= cutoff_90d]
        recent_50 = sorted(all_reviews, key=lambda x: x.get("created", ""), reverse=True)[:50]

        # Monthly trend (last 12 months)
        from collections import defaultdict
        by_month_ratings = defaultdict(list)
        for r in all_reviews:
            dt = _parse_dt(r.get("created", ""))
            if dt is None:
                continue
            key = dt.strftime("%Y-%m")
            by_month_ratings[key].append(int(r["rating"]))
        monthly = []
        for key in sorted(by_month_ratings.keys())[-12:]:
            ratings = by_month_ratings[key]
            avg = round(sum(ratings) / len(ratings), 2)
            share = round(100 * sum(1 for r in ratings if r >= 4) / len(ratings), 1)
            monthly.append({
                "month": key,
                "count": len(ratings),
                "avg": avg,
                "share_4plus": share,
            })

        newest_10 = sorted(all_reviews, key=lambda x: x.get("created", ""), reverse=True)[:10]
        reviews_recent_out = [
            {
                "rating": int(r["rating"]),
                "title": r.get("title", ""),
                "body": r.get("body", ""),
                "reviewer": r.get("reviewer", ""),
                "territory": r.get("territory", ""),
                "created": r.get("created", ""),
            }
            for r in newest_10
        ]

        stats_30d = _stats(last_30d)
        stats_90d = _stats(last_90d)
        stats_all = _stats(all_reviews)
        stats_recent50 = _stats(recent_50)

        # ---- Subscription sales (last ~30 days) ----
        # Requires Finance role on the API key AND a vendor number.
        subs_data = {"status": "skipped", "reason": "no vendor_number"}
        if vendor_number:
            from datetime import date as _date, timedelta as _td
            today = _date.today()
            all_rows = []
            attempted = 0
            success_dates = []
            # Reports lag 1-2 days; fetch d-2 through d-32.
            for days_back in range(2, 33):
                rd = (today - _td(days=days_back)).isoformat()
                attempted += 1
                rows = _fetch_asc_daily_sales(token, vendor_number, rd)
                if rows:
                    success_dates.append(rd)
                    for r in rows:
                        r["_report_date"] = rd
                    all_rows.extend(rows)
            summary = _summarize_asc_sales(all_rows, bundle_prefix)

            # Active subscribers (SUBSCRIPTION status report) -- separate from event-based sales
            active_count = None
            active_breakdown = None
            for days_back in range(2, 10):
                rd = (today - _td(days=days_back)).isoformat()
                status_rows = _fetch_asc_subscription_status(token, vendor_number, str(app_id) if app_id else "", rd)
                if status_rows:
                    active_breakdown = _summarize_asc_subscription_status(status_rows)
                    active_count = active_breakdown["active_total"]
                    active_breakdown["as_of"] = rd
                    break

            # Subscription events (SUBSCRIPTION_EVENT report) -- last 30 days
            from collections import Counter as _Counter
            event_counts = _Counter()
            event_days = 0
            for days_back in range(2, 33):
                rd = (today - _td(days=days_back)).isoformat()
                ev_rows = _fetch_asc_subscription_event(token, vendor_number, str(app_id) if app_id else "", rd)
                if ev_rows:
                    event_days += 1
                    for r in ev_rows:
                        ev = (r.get("Event", "") or "").strip()
                        try:
                            q = int(r.get("Quantity", "1") or 1)
                        except ValueError:
                            q = 1
                        if ev:
                            event_counts[ev] += q

            # Monthly churn = Cancel events over 30 days / active subscribers
            cancel_events_30d = sum(v for k, v in event_counts.items() if "cancel" in k.lower())
            refund_events_30d = sum(v for k, v in event_counts.items() if "refund" in k.lower())
            monthly_churn = None
            if active_count and active_count > 0:
                monthly_churn = round(cancel_events_30d / active_count, 4)

            subs_data = {
                "status": "ok" if success_dates else "empty",
                "window_start": min(success_dates) if success_dates else None,
                "window_end": max(success_dates) if success_dates else None,
                "days_with_data": len(success_dates),
                "days_attempted": attempted,
                "active_subscribers": active_count,
                "active_breakdown": active_breakdown,
                "events_30d": dict(event_counts),
                "event_days_with_data": event_days,
                "cancel_events_30d": cancel_events_30d,
                "refund_events_30d": refund_events_30d,
                "monthly_churn": monthly_churn,
                **summary,
            }

        return {
            "status": "ok",
            "app_id": app_id,
            "app_name": app_name,
            "bundle_id": bundle_id,
            "reviews_recent": reviews_recent_out,
            "new_this_run": new_count,
            # legacy keys for renderer back-compat (recent-50)
            "reviews_count_recent": stats_recent50["count"],
            "avg_rating_recent": stats_recent50["avg"],
            "rating_distribution_recent": stats_recent50["dist"],
            "rating_count_recent": stats_recent50["count"],
            # rolling stats
            "stats_30d": stats_30d,
            "stats_90d": stats_90d,
            "stats_all_time": stats_all,
            "monthly": monthly,
            # subscription / sales data
            "subscriptions": subs_data,
            "fetched_at": _now_iso(),
        }
    except urllib.error.HTTPError as e:
        body = e.read()[:300].decode("utf-8", "replace")
        return {"status": "error", "error": f"HTTP {e.code}", "body": body}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


# ---------- Bluesky ----------
def fetch_bluesky() -> dict:
    handle = os.environ.get("BLUESKY_HANDLE")
    password = os.environ.get("BLUESKY_PASSWORD")
    if not (handle and password):
        return {"status": "skipped", "reason": "Bluesky credentials missing"}
    try:
        # Create session
        sess = _http_get(
            "https://bsky.social/xrpc/com.atproto.server.createSession?",
            timeout=20,
        ) if False else None
        req = urllib.request.Request(
            "https://bsky.social/xrpc/com.atproto.server.createSession",
            data=json.dumps({"identifier": handle, "password": password}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            sess = json.loads(r.read())
        access_jwt = sess["accessJwt"]
        did = sess["did"]
        auth = {"Authorization": f"Bearer {access_jwt}"}

        # Profile
        profile = _http_get(
            f"https://bsky.social/xrpc/app.bsky.actor.getProfile?actor={urllib.parse.quote(handle)}",
            auth,
        )

        # Recent posts (7d)
        feed = _http_get(
            f"https://bsky.social/xrpc/app.bsky.feed.getAuthorFeed?actor={did}&limit=30",
            auth,
        )
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        likes_7d = 0
        reposts_7d = 0
        posts_7d = 0
        for item in feed.get("feed", []):
            post = item.get("post", {})
            indexed_at = post.get("indexedAt", "")
            try:
                pdt = datetime.fromisoformat(indexed_at.replace("Z", "+00:00"))
                if pdt < cutoff:
                    continue
            except Exception:
                continue
            posts_7d += 1
            likes_7d += post.get("likeCount", 0)
            reposts_7d += post.get("repostCount", 0)

        return {
            "status": "ok",
            "handle": handle,
            "followers": profile.get("followersCount", 0),
            "following": profile.get("followsCount", 0),
            "posts_total": profile.get("postsCount", 0),
            "posts_7d": posts_7d,
            "likes_7d": likes_7d,
            "reposts_7d": reposts_7d,
            "fetched_at": _now_iso(),
        }
    except urllib.error.HTTPError as e:
        return {"status": "error", "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


# ---------- Mastodon ----------
def fetch_mastodon() -> dict:
    instance = os.environ.get("MASTODON_INSTANCE")
    token = os.environ.get("MASTODON_ACCESS_TOKEN")
    if not (instance and token):
        return {"status": "skipped", "reason": "Mastodon credentials missing"}
    try:
        headers = {"Authorization": f"Bearer {token}"}
        base = f"https://{instance}"
        # Verify credentials → returns current user account
        me = _http_get(f"{base}/api/v1/accounts/verify_credentials", headers)
        acc_id = me["id"]
        followers = me.get("followers_count", 0)
        following = me.get("following_count", 0)
        statuses_total = me.get("statuses_count", 0)

        # Recent statuses (last 40) — soft-fail if scope is missing
        posts_7d = 0
        favs_7d = 0
        boosts_7d = 0
        try:
            statuses = _http_get(
                f"{base}/api/v1/accounts/{acc_id}/statuses?limit=40&exclude_replies=true",
                headers,
            )
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            for s in statuses:
                try:
                    pdt = datetime.fromisoformat(s["created_at"].replace("Z", "+00:00"))
                    if pdt < cutoff:
                        continue
                except Exception:
                    continue
                posts_7d += 1
                favs_7d += s.get("favourites_count", 0)
                boosts_7d += s.get("reblogs_count", 0)
        except Exception:
            # Scope missing or instance restricted — keep followers data, lose engagement
            pass

        return {
            "status": "ok",
            "instance": instance,
            "username": me.get("username"),
            "followers": followers,
            "following": following,
            "posts_total": statuses_total,
            "posts_7d": posts_7d,
            "favs_7d": favs_7d,
            "boosts_7d": boosts_7d,
            "fetched_at": _now_iso(),
        }
    except urllib.error.HTTPError as e:
        return {"status": "error", "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


# ---------- Threads ----------
def fetch_threads() -> dict:
    token = os.environ.get("THREADS_ACCESS_TOKEN")
    user_id = os.environ.get("THREADS_USER_ID")
    if not (token and user_id):
        return {"status": "skipped", "reason": "Threads credentials missing"}
    try:
        base = "https://graph.threads.net/v1.0"
        # Account-level fields
        me = _http_get(
            f"{base}/{user_id}?fields=id,username,threads_profile_picture_url&access_token={token}"
        )
        username = me.get("username", "")

        # Followers via insights (requires threads_manage_insights scope)
        followers = None
        try:
            insights = _http_get(
                f"{base}/{user_id}/threads_insights?metric=followers_count&access_token={token}"
            )
            for m in insights.get("data", []):
                if m.get("name") == "followers_count":
                    followers = m.get("total_value", {}).get("value")
                    break
        except Exception:
            pass

        # Recent threads (last 25) for 7-day engagement
        posts_7d = 0
        likes_7d = 0
        replies_7d = 0
        reposts_7d = 0
        try:
            threads = _http_get(
                f"{base}/{user_id}/threads?fields=id,timestamp&limit=25&access_token={token}"
            )
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            for t in threads.get("data", []):
                try:
                    pdt = datetime.fromisoformat(t["timestamp"].replace("Z", "+00:00"))
                    if pdt < cutoff:
                        continue
                except Exception:
                    continue
                posts_7d += 1
                # Per-thread insights
                try:
                    ins = _http_get(
                        f"{base}/{t['id']}/insights?metric=likes,replies,reposts&access_token={token}"
                    )
                    for m in ins.get("data", []):
                        name = m.get("name")
                        val = m.get("values", [{}])[0].get("value", 0) if m.get("values") else m.get("total_value", {}).get("value", 0)
                        if name == "likes":
                            likes_7d += val or 0
                        elif name == "replies":
                            replies_7d += val or 0
                        elif name == "reposts":
                            reposts_7d += val or 0
                except Exception:
                    pass
        except Exception:
            pass

        return {
            "status": "ok",
            "handle": f"@{username}" if username else "",
            "username": username,
            "followers": followers,
            "posts_7d": posts_7d,
            "likes_7d": likes_7d,
            "comments_7d": replies_7d,
            "reposts_7d": reposts_7d,
            "fetched_at": _now_iso(),
        }
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        return {"status": "error", "error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


def fetch_instagram() -> dict:
    token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    user_id = os.environ.get("INSTAGRAM_USER_ID")
    if not (token and user_id):
        return {"status": "skipped", "reason": "Instagram credentials missing"}
    try:
        base = "https://graph.instagram.com"
        # Account-level fields
        me = _http_get(
            f"{base}/{user_id}?fields=id,username,account_type,followers_count,follows_count,media_count&access_token={token}"
        )
        followers = me.get("followers_count", 0)
        following = me.get("follows_count", 0)
        media_total = me.get("media_count", 0)

        # Recent media (last 25) for 7-day engagement
        posts_7d = 0
        likes_7d = 0
        comments_7d = 0
        try:
            media = _http_get(
                f"{base}/{user_id}/media?fields=id,timestamp,like_count,comments_count&limit=25&access_token={token}"
            )
            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            for m in media.get("data", []):
                try:
                    pdt = datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00"))
                    if pdt < cutoff:
                        continue
                except Exception:
                    continue
                posts_7d += 1
                likes_7d += m.get("like_count", 0)
                comments_7d += m.get("comments_count", 0)
        except Exception:
            pass

        return {
            "status": "ok",
            "handle": f"@{me.get('username')}" if me.get("username") else "",
            "username": me.get("username"),
            "account_type": me.get("account_type"),
            "followers": followers,
            "following": following,
            "posts_total": media_total,
            "posts_7d": posts_7d,
            "likes_7d": likes_7d,
            "comments_7d": comments_7d,
            "fetched_at": _now_iso(),
        }
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        return {"status": "error", "error": f"HTTP {e.code}: {body}"}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


# ---------- Push notification stats ----------
def fetch_push_stats() -> dict:
    """Read push_history.csv from state/ directory."""
    push_csv = REPO_ROOT / "state" / "push_history.csv"
    if not push_csv.exists():
        return {"status": "skipped", "reason": "no push_history.csv"}
    try:
        import csv
        rows = []
        with push_csv.open() as f:
            for row in csv.DictReader(f):
                rows.append(row)
        # Sort by sent date desc
        rows.sort(key=lambda r: r.get("sent_at", ""), reverse=True)
        return {
            "status": "ok",
            "total_pushes": len(rows),
            "recent": rows[:10],
            "fetched_at": _now_iso(),
        }
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


# ---------- Roadmap ----------
def fetch_roadmap() -> dict:
    path = REPO_ROOT / "ROADMAP.md"
    if not path.exists():
        return {"status": "skipped", "reason": "ROADMAP.md missing"}
    text = path.read_text()
    sections = {"in_progress": [], "upcoming": [], "blocked": [], "completed": []}
    current = None
    for line in text.splitlines():
        line = line.rstrip()
        m = re.match(r"^##\s+(.+)$", line)
        if m:
            head = m.group(1).strip().lower().replace(" ", "_")
            if head in sections:
                current = head
            else:
                current = None
            continue
        m = re.match(r"^-\s+(.+)$", line)
        if m and current:
            item = m.group(1).strip()
            if "::" in item:
                title, note = item.split("::", 1)
                sections[current].append(
                    {"title": title.strip(), "note": note.strip()}
                )
            else:
                sections[current].append({"title": item, "note": ""})
    return {"status": "ok", **sections, "fetched_at": _now_iso()}


# ---------- Strategy targets (hardcoded, mirrors STRATEGY.md) ----------
def fetch_targets() -> dict:
    return {
        "status": "ok",
        "north_star": {
            "metric": "DAU (latest day)",
            "current_label": "DAU (latest)",
            "target": 500,
            "target_date": "2026-08-31",
        },
        "supporting": [
            {"key": "dau_latest", "label": "DAU (latest)", "target": 500, "format": "int"},
            {"key": "active_28d", "label": "28-day active users", "target": 12000, "format": "int"},
            {"key": "kit_subscribers", "label": "Newsletter subs (Kit)", "target": 250, "format": "int"},
            {"key": "plus_subscribers", "label": "Artemis Plus subs", "target": 250, "format": "int"},
            {"key": "monthly_churn", "label": "Monthly churn (Plus)", "target": 6, "format": "pct_lower"},
            {"key": "push_opt_in", "label": "Push opt-in (iOS)", "target": 35, "format": "pct"},
            {"key": "push_open_rate", "label": "Push open rate (30d)", "target": 25, "format": "pct"},
            {"key": "new_installs_30d", "label": "New installs / 30d", "target": 3000, "format": "int"},
            {"key": "avg_rating", "label": "App Store rating (avg)", "target": 4.6, "format": "float"},
            {"key": "reviews_4plus", "label": "4★+ reviews count", "target": 100, "format": "int"},
            {"key": "bluesky_followers", "label": "Bluesky followers", "target": 750, "format": "int"},
            {"key": "mastodon_followers", "label": "Mastodon followers", "target": 300, "format": "int"},
        ],
        "installed_base": {
            "ios": 50000,
            "android": 2000,
            "total": 52000,
        },
        "monetization_long_term": {
            "share_of_installed_base": 0.10,
            "implied_subs": 5200,
        },
    }


# =============================================================================
# Google Play Console — subscription metrics
# =============================================================================

def _play_bucket() -> str | None:
    return os.environ.get("GOOGLE_PLAY_REPORTS_BUCKET") or "pubsite_prod_6157935083484095024"


def _play_package() -> str:
    return os.environ.get("GOOGLE_PLAY_PACKAGE") or "no.bitfactory.artemisii.tracker"


def _play_credentials():
    """Build Google credentials from GOOGLE_PLAY_SERVICE_ACCOUNT_JSON or local file."""
    from google.oauth2 import service_account

    json_blob = os.environ.get("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON")
    if json_blob:
        info = json.loads(json_blob)
    else:
        local = Path("/home/user/workspace/secrets/playconsole/service-account.json")
        if not local.exists():
            return None
        info = json.loads(local.read_text())
    scopes = ["https://www.googleapis.com/auth/devstorage.read_only"]
    return service_account.Credentials.from_service_account_info(info, scopes=scopes)


def _gcs_list(bucket: str, prefix: str, creds) -> list[str]:
    """List object names in a GCS bucket with given prefix using JSON API."""
    from google.auth.transport.requests import Request

    if not creds.valid:
        creds.refresh(Request())
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o?prefix={urllib.parse.quote(prefix)}&maxResults=1000"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {creds.token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
    return [item["name"] for item in data.get("items", [])]


def _gcs_get(bucket: str, name: str, creds) -> bytes:
    from google.auth.transport.requests import Request

    if not creds.valid:
        creds.refresh(Request())
    url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o/{urllib.parse.quote(name, safe='')}?alt=media"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {creds.token}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def _parse_play_subscriptions_zip(blob: bytes) -> list[dict]:
    """Extract rows from a Play subscriptions monthly zip. CSV columns include
    Package Name, Product ID, Country, Buyer Currency, Amount (Buyer Currency),
    Buyer Postal Code, Event Date, Event Timestamp, Original Order Id, Order
    Number, Event Type (e.g. New, Renewal, Cancel)."""
    rows = []
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        for member in zf.namelist():
            if not member.endswith(".csv"):
                continue
            raw = zf.read(member)
            # Play reports are utf-16 with BOM
            try:
                text = raw.decode("utf-16")
            except UnicodeDecodeError:
                text = raw.decode("utf-8", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            for row in reader:
                rows.append({k.strip(): (v.strip() if v else "") for k, v in row.items()})
    return rows


def _parse_play_earnings_zip(blob: bytes) -> list[dict]:
    """Extract rows from a Play earnings monthly zip. Provides merchant proceeds
    in merchant currency. Columns include Transaction Date, Product ID,
    Product Type, Sku Id, Buyer Country, Amount (Merchant Currency), Merchant
    Currency, Tax Type, Refund."""
    return _parse_play_subscriptions_zip(blob)  # same gz format


def _months_back(n: int) -> list[str]:
    """Return list of YYYYMM strings going n months back from today (inclusive of current)."""
    today = datetime.now(timezone.utc).date()
    out = []
    for i in range(n):
        y = today.year
        m = today.month - i
        while m <= 0:
            m += 12
            y -= 1
        out.append(f"{y:04d}{m:02d}")
    return out


def fetch_play_console() -> dict:
    """Fetch Google Play subscription + earnings metrics for Artemis Tracker.

    Returns last-30-days aggregate similar to App Store Connect:
      - total_units_30d, total_proceeds_usd_30d, new_subscribers_30d
      - by_product, by_day, by_country, by_event_type
    """
    try:
        creds = _play_credentials()
        if creds is None:
            return {"status": "skipped", "reason": "no Play service account credentials"}
        bucket = _play_bucket()
        package = _play_package()
        if not bucket:
            return {"status": "skipped", "reason": "no GOOGLE_PLAY_REPORTS_BUCKET"}

        # Fetch last 3 months of subscription + earnings reports
        months = _months_back(3)
        sub_rows: list[dict] = []
        earn_rows: list[dict] = []

        for ym in months:
            # Subscription reports
            try:
                names = _gcs_list(bucket, f"stats/subscriptions/subscriptions_{ym}_{package}", creds)
                for n in names:
                    if n.endswith(".zip"):
                        try:
                            blob = _gcs_get(bucket, n, creds)
                            sub_rows.extend(_parse_play_subscriptions_zip(blob))
                        except Exception:
                            pass
            except Exception:
                pass

            # Earnings (proceeds in USD typically)
            try:
                names = _gcs_list(bucket, f"earnings/earnings_{ym}", creds)
                for n in names:
                    if n.endswith(".zip"):
                        try:
                            blob = _gcs_get(bucket, n, creds)
                            earn_rows.extend(_parse_play_earnings_zip(blob))
                        except Exception:
                            pass
            except Exception:
                pass

        return _summarize_play(sub_rows, earn_rows, package)

    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


def _summarize_play(sub_rows: list[dict], earn_rows: list[dict], package: str) -> dict:
    """Aggregate Play subscription + earnings rows into 30-day dashboard view."""
    today = datetime.now(timezone.utc).date()
    window_start = today - timedelta(days=29)

    def _row_date(row: dict) -> str | None:
        for k in ("Event Date", "Transaction Date", "Order Charged Date"):
            v = row.get(k)
            if v:
                return v[:10]
        return None

    def _in_window(row: dict) -> bool:
        d = _row_date(row)
        if not d:
            return False
        try:
            dt = datetime.strptime(d, "%Y-%m-%d").date()
            return window_start <= dt <= today
        except ValueError:
            return False

    sub_window = [r for r in sub_rows if _in_window(r)]
    earn_window = [r for r in earn_rows if _in_window(r) and (r.get("Product Type") or "").lower().startswith("subscript")]

    # Filter earnings to subscriptions only (Product Type starts with "Subscription")
    # If "Product Type" column missing, fall back to filtering by product id prefix
    if not earn_window and earn_rows:
        earn_window = [r for r in earn_rows if _in_window(r) and ("monthly" in (r.get("Product Id") or r.get("Sku Id") or "") or "yearly" in (r.get("Product Id") or r.get("Sku Id") or ""))]

    # Aggregate by product (units = subscription events, prefer "New" + "Renewal" types)
    by_product: dict = {}
    by_event_type: dict = {}
    by_country: dict = {}
    by_day_map: dict = {}
    new_subs = 0

    for row in sub_window:
        product_id = row.get("Product ID") or row.get("Product Id") or row.get("Sku Id") or "unknown"
        event = row.get("Event Type") or row.get("Subscription Event Type") or "Unknown"
        country = row.get("Buyer Country") or row.get("Country") or "??"
        date = _row_date(row) or ""

        by_event_type[event] = by_event_type.get(event, 0) + 1

        # Count as "unit" if event is a billing event (New / Renewal)
        is_billing = event in ("New", "Renewal") or "renew" in event.lower() or "purchase" in event.lower() or event == ""
        if is_billing:
            entry = by_product.setdefault(product_id, {"units": 0, "proceeds_usd": 0.0, "name": product_id})
            entry["units"] += 1
            by_country[country] = by_country.get(country, {"units": 0, "proceeds_usd": 0.0})
            by_country[country]["units"] += 1
            day = by_day_map.setdefault(date, {"date": date, "monthly": 0, "yearly": 0, "other": 0, "proceeds_usd": 0.0})
            if product_id.endswith(".monthly"):
                day["monthly"] += 1
            elif product_id.endswith(".yearly"):
                day["yearly"] += 1
            else:
                day["other"] += 1
        if event == "New" or "new" in event.lower():
            new_subs += 1

    # Aggregate proceeds (merchant currency, treated as USD for now)
    for row in earn_window:
        product_id = row.get("Product ID") or row.get("Product Id") or row.get("Sku Id") or "unknown"
        country = row.get("Buyer Country") or row.get("Country") or "??"
        date = _row_date(row) or ""
        amount_str = row.get("Amount (Merchant Currency)") or row.get("Merchant Proceeds") or "0"
        try:
            amount = float(str(amount_str).replace(",", "."))
        except ValueError:
            amount = 0.0

        if product_id in by_product:
            by_product[product_id]["proceeds_usd"] += amount
        if country in by_country:
            by_country[country]["proceeds_usd"] += amount
        if date in by_day_map:
            by_day_map[date]["proceeds_usd"] += amount

    # Convert maps to sorted lists
    by_day = sorted(by_day_map.values(), key=lambda d: d["date"])
    by_country_list = sorted(
        [{"country": k, **v} for k, v in by_country.items()],
        key=lambda c: c["units"],
        reverse=True,
    )

    total_units = sum(p["units"] for p in by_product.values())
    total_proceeds = round(sum(p["proceeds_usd"] for p in by_product.values()), 2)

    return {
        "status": "ok",
        "window_start": window_start.isoformat(),
        "window_end": today.isoformat(),
        "package": package,
        "by_product": by_product,
        "by_day": by_day,
        "by_country": by_country_list,
        "by_event_type": by_event_type,
        "total_units_30d": total_units,
        "total_proceeds_usd_30d": total_proceeds,
        "new_subscribers_30d": new_subs,
        "sub_rows_seen": len(sub_rows),
        "earn_rows_seen": len(earn_rows),
    }


def fetch_all() -> dict:
    return {
        "ga4": fetch_ga4(),
        "kit": fetch_kit(),
        "asc": fetch_app_store_connect(),
        "play": fetch_play_console(),
        "bluesky": fetch_bluesky(),
        "mastodon": fetch_mastodon(),
        "threads": fetch_threads(),
        "instagram": fetch_instagram(),
        "push": fetch_push_stats(),
        "roadmap": fetch_roadmap(),
        "targets": fetch_targets(),
        "generated_at": _now_iso(),
    }


if __name__ == "__main__":
    data = fetch_all()
    print(json.dumps(data, indent=2, default=str))
