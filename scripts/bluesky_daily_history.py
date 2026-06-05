#!/usr/bin/env python3
"""Post 'on this day in spaceflight history' to Bluesky if an entry exists for today.

Silent skip if no entry for today's MM-DD. Logs every run (posted/skipped/error)
to state/bluesky_daily_log.txt.

Reads curated events from state/spaceflight_history.json (a dict keyed by 'MM-DD',
each value a list of {year, event, source_url}).
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = REPO_ROOT / "state"
HISTORY = STATE_DIR / "spaceflight_history.json"
LOG = STATE_DIR / "bluesky_daily_log.txt"
WORKSPACE = Path("/home/user/workspace")
BLUESKY_CFG = WORKSPACE / "bluesky_config.json"


def log(line: str):
    STATE_DIR.mkdir(exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now(timezone.utc).isoformat()} | {line}\n")


def login(handle: str, app_password: str) -> dict:
    r = requests.post(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        json={"identifier": handle, "password": app_password},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def create_post(session: dict, text: str) -> dict:
    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    r = requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {session['accessJwt']}"},
        json={"repo": session["did"], "collection": "app.bsky.feed.post", "record": record},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def main():
    if not HISTORY.exists():
        log("skipped | reason=no_history_file")
        return
    history = json.loads(HISTORY.read_text(encoding="utf-8"))
    today = datetime.now(timezone.utc).strftime("%m-%d")
    entries = history.get(today, [])
    if not entries:
        log(f"skipped | date={today} | reason=no_entry")
        return

    entry = entries[0]
    year = entry.get("year", "")
    event = entry.get("event", "")
    source = entry.get("source_url", "")
    text = f"On this day, {year}: {event}"
    if source:
        text = f"{text}\n\n{source}"
    if len(text) > 300:
        text = text[:297] + "..."

    try:
        cfg = json.loads(BLUESKY_CFG.read_text())
        session = login(cfg["handle"], cfg["app_password"])
        result = create_post(session, text)
        log(f"posted | date={today} | year={year} | uri={result['uri']}")
        print(result["uri"])
    except Exception as e:
        log(f"error | date={today} | {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
