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
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
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


def fetch_app_store_connect() -> dict:
    key_id = os.environ.get("APP_STORE_CONNECT_KEY_ID")
    issuer_id = os.environ.get("APP_STORE_CONNECT_ISSUER_ID")
    private_key = os.environ.get("APP_STORE_CONNECT_PRIVATE_KEY")
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

        # Customer reviews
        reviews_url = (
            f"https://api.appstoreconnect.apple.com/v1/apps/{app_id}/customerReviews"
            "?limit=50&sort=-createdDate"
        )
        try:
            reviews_data = _http_get(reviews_url, headers)
            reviews_raw = reviews_data.get("data", [])
            reviews = []
            rating_sum = 0
            rating_count = 0
            for r in reviews_raw:
                attr = r.get("attributes", {})
                rating = attr.get("rating", 0)
                rating_sum += rating
                rating_count += 1
                reviews.append({
                    "rating": rating,
                    "title": attr.get("title", "")[:120],
                    "body": attr.get("body", "")[:200],
                    "reviewer": attr.get("reviewerNickname", ""),
                    "territory": attr.get("territory", ""),
                    "created": attr.get("createdDate", ""),
                })
            avg_rating = round(rating_sum / rating_count, 2) if rating_count else None
            # Distribution
            dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for r in reviews:
                if r["rating"] in dist:
                    dist[r["rating"]] += 1
        except Exception as e:
            reviews = []
            avg_rating = None
            dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            rating_count = 0

        return {
            "status": "ok",
            "app_id": app_id,
            "app_name": app_name,
            "bundle_id": bundle_id,
            "reviews_recent": reviews[:10],
            "reviews_count_recent": len(reviews),
            "avg_rating_recent": avg_rating,
            "rating_distribution_recent": dist,
            "rating_count_recent": rating_count,
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

        # Recent statuses (last 40)
        statuses = _http_get(
            f"{base}/api/v1/accounts/{acc_id}/statuses?limit=40&exclude_replies=true",
            headers,
        )
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        posts_7d = 0
        favs_7d = 0
        boosts_7d = 0
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


# ---------- Threads / Instagram — placeholder ----------
def fetch_threads() -> dict:
    return {
        "status": "blocked",
        "reason": "Meta developer verification not completed — publishing and metrics disabled",
        "fetched_at": _now_iso(),
    }


def fetch_instagram() -> dict:
    return {
        "status": "blocked",
        "reason": "Needs Business/Creator account linked to Facebook page + instagram_content_publish approval",
        "fetched_at": _now_iso(),
    }


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


def fetch_all() -> dict:
    return {
        "ga4": fetch_ga4(),
        "kit": fetch_kit(),
        "asc": fetch_app_store_connect(),
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
