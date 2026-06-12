#!/usr/bin/env python3
"""Post a curated news commentary to Bluesky.

Reads a candidate JSON from /tmp/bluesky_candidate.json with shape:
    {
      "headline": "...",
      "url": "...",
      "source": "SpaceNews",
      "key_fact": "1-2 sentence fact",
      "implication": "1 sentence editorial"
    }

Dedup: refuses to post if the URL is already in state/bluesky_posted_urls.log.
Logs every run to state/bluesky_news_log.txt.
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = REPO_ROOT / "state"
POSTED_URLS = STATE_DIR / "bluesky_posted_urls.log"
LOG = STATE_DIR / "bluesky_news_log.txt"
from _creds import load_bluesky

WORKSPACE = Path("/home/user/workspace")
CANDIDATE = Path("/tmp/bluesky_candidate.json")
BLUESKY_CFG = WORKSPACE / "bluesky_config.json"

MAX_CHARS = 280


def log(line: str):
    STATE_DIR.mkdir(exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} | {line}\n")


def already_posted(url: str) -> bool:
    if not POSTED_URLS.exists():
        return False
    return url in POSTED_URLS.read_text(encoding="utf-8").splitlines()


def mark_posted(url: str):
    STATE_DIR.mkdir(exist_ok=True)
    with POSTED_URLS.open("a", encoding="utf-8") as f:
        f.write(url + "\n")


def login(handle: str, app_password: str) -> dict:
    r = requests.post(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        json={"identifier": handle, "password": app_password},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def fetch_link_card(url: str) -> dict | None:
    """Build an external embed for Bluesky from the article URL."""
    try:
        html = requests.get(url, timeout=15, headers={"User-Agent": "ArtemisTracker/1.0"}).text
    except Exception:
        return None

    def find_meta(prop: str) -> str | None:
        # crude og:* lookup
        import re
        m = re.search(rf'<meta[^>]+property=["\']{prop}["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
        if not m:
            m = re.search(rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{prop}["\']', html, re.I)
        return m.group(1) if m else None

    title = find_meta("og:title") or ""
    desc = find_meta("og:description") or ""
    return {
        "$type": "app.bsky.embed.external",
        "external": {"uri": url, "title": title[:300], "description": desc[:500]},
    }


def create_post(session: dict, text: str, embed: dict | None) -> dict:
    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if embed:
        record["embed"] = embed
    r = requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {session['accessJwt']}"},
        json={"repo": session["did"], "collection": "app.bsky.feed.post", "record": record},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def compose(candidate: dict) -> str:
    key_fact = candidate["key_fact"].strip()
    implication = candidate["implication"].strip()
    source = candidate.get("source", "")
    suffix = f" ({source})" if source else ""
    text = f"{key_fact}\n\n{implication}{suffix}"
    if len(text) > MAX_CHARS:
        # trim implication
        budget = MAX_CHARS - len(key_fact) - len(suffix) - 4
        if budget < 40:
            text = key_fact[: MAX_CHARS - len(suffix) - 1] + suffix
        else:
            text = f"{key_fact}\n\n{implication[:budget].rstrip()}…{suffix}"
    return text


def main():
    if not CANDIDATE.exists():
        log("error | no candidate file at /tmp/bluesky_candidate.json")
        print("No candidate file", file=sys.stderr)
        sys.exit(1)

    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    url = candidate["url"]

    if already_posted(url):
        log(f"skipped | reason=duplicate | url={url}")
        print("Already posted, skipping")
        return

    text = compose(candidate)
    embed = fetch_link_card(url)

    try:
        cfg = load_bluesky()
        session = login(cfg["handle"], cfg["password"])
        result = create_post(session, text, embed)
        mark_posted(url)
        log(f"posted | uri={result['uri']} | url={url}")
        print(result["uri"])
    except Exception as e:
        log(f"error | {type(e).__name__}: {e} | url={url}")
        sys.exit(1)


if __name__ == "__main__":
    main()
