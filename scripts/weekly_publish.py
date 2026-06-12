#!/usr/bin/env python3
"""
Orchestrates the weekly Artemis Tracker publish flow.

Reads a draft from drafts/{article_id}/article_draft.md (+ hero.jpg), then:
1. Copies hero to updates/images/{article_id}.jpg
2. Writes article body to updates/articles/{article_id}.md
3. Inserts new entry at top of updates/manifest.json
4. Sends FCM push
5. Schedules Kit newsletter for tonight 21:30 CEST
6. Posts thread to Bluesky + Mastodon
7. Appends to state/publish_history.txt

All commits + push happen in the workflow after this script returns.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml  # PyYAML

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
DRAFTS = REPO_ROOT / "drafts"
UPDATES = REPO_ROOT / "updates"
ARTICLES = UPDATES / "articles"
IMAGES = UPDATES / "images"
MANIFEST = UPDATES / "manifest.json"
STATE = REPO_ROOT / "state"
PUBLISH_LOG = STATE / "publish_history.txt"

from _creds import load_kit


def parse_draft(article_id: str):
    draft_dir = DRAFTS / article_id
    md = draft_dir / "article_draft.md"
    hero = draft_dir / "hero.jpg"
    if not md.exists():
        raise SystemExit(f"Missing {md}")
    if not hero.exists():
        raise SystemExit(f"Missing {hero}")
    text = md.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise SystemExit("Draft has no frontmatter")
    _, fm, body = text.split("---", 2)
    meta = yaml.safe_load(fm)
    return meta, body.lstrip("\n"), hero


def copy_assets(article_id: str, body: str, hero: Path):
    ARTICLES.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(parents=True, exist_ok=True)
    shutil.copy2(hero, IMAGES / f"{article_id}.jpg")
    (ARTICLES / f"{article_id}.md").write_text(body, encoding="utf-8")


def update_manifest(meta: dict, article_id: str):
    if MANIFEST.exists():
        data = json.loads(MANIFEST.read_text())
    else:
        data = {"updates": []}
    hero_url = f"https://grandmasterjc.github.io/artemis2-config/updates/images/{article_id}.jpg"
    summary = (meta.get("subtitle") or "")[:200]
    entry = {
        "id": article_id,
        "title": meta["title"],
        "subtitle": meta.get("subtitle", ""),
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mission": meta.get("mission", "artemis3"),
        "premium": bool(meta.get("premium", False)),
        "hero_image": hero_url,
        "summary": summary,
        "author": "Joachim Gresslien",
    }
    data["updates"].insert(0, entry)
    MANIFEST.write_text(json.dumps(data, indent=2))
    print(f"manifest: inserted {article_id} at top")


def send_push(push_title: str, push_body: str, article_id: str):
    out = subprocess.check_output(
        [sys.executable, str(SCRIPTS / "send_push.py"),
         push_title, push_body, article_id, "all"],
        cwd=str(REPO_ROOT),
    ).decode().strip()
    print(f"push sent: {out}")
    return out


def schedule_kit_newsletter(meta: dict, body: str, article_id: str) -> str:
    sys.path.insert(0, str(SCRIPTS))
    from kit_template import build_newsletter_html

    cfg = load_kit()
    api_key = cfg["api_key"]
    hero_url = f"https://grandmasterjc.github.io/artemis2-config/updates/images/{article_id}.jpg"

    # First 3-4 paragraphs of body
    paras = [p for p in body.split("\n\n") if p.strip() and not p.strip().startswith("---")][:4]
    tease_body = "\n\n".join(paras)
    tease_body += "\n\n[Read the full piece in the app](https://apps.apple.com/app/id6761183798)"

    # Merch
    merch = None
    merch_manifest = REPO_ROOT / "merch" / "manifest.json"
    if merch_manifest.exists():
        mdata = json.loads(merch_manifest.read_text())
        actives = [p for p in mdata.get("products", []) if p.get("active")]
        if actives:
            merch = actives[0]

    html = build_newsletter_html(
        hero_url, meta["title"], tease_body,
        merch_product=merch,
        include_week_ahead_cta=True,
    )

    # Schedule for tonight 21:30 CEST
    now = datetime.now(timezone.utc)
    cest_offset = timedelta(hours=2)  # CEST is UTC+2 in summer
    today_2130_cest = (now + cest_offset).replace(hour=21, minute=30, second=0, microsecond=0)
    send_at_utc = today_2130_cest - cest_offset
    if send_at_utc < now + timedelta(minutes=5):
        send_at_utc = now + timedelta(minutes=10)

    payload = {
        "subject": meta["push_title"],
        "content": html,
        "description": (meta["push_body"][:140]),
        "preview_text": (meta["push_body"][:140]),
        "public": True,
        "send_at": send_at_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    req = urllib.request.Request(
        "https://api.kit.com/v4/broadcasts",
        data=json.dumps(payload).encode(),
        headers={"X-Kit-Api-Key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read())
    broadcast_id = result.get("broadcast", {}).get("id") or result.get("id")
    print(f"kit broadcast scheduled: {broadcast_id} for {send_at_utc.isoformat()}")
    return str(broadcast_id)


def post_social(article_id: str) -> tuple[str, str]:
    draft_md = DRAFTS / article_id / "article_draft.md"
    hero_url = f"https://grandmasterjc.github.io/artemis2-config/updates/images/{article_id}.jpg"
    out = subprocess.check_output(
        [sys.executable, str(SCRIPTS / "social_publish.py"),
         str(draft_md), hero_url],
        cwd=str(REPO_ROOT),
    ).decode().strip()
    result = json.loads(out.splitlines()[-1])
    return result.get("bluesky_uri", ""), result.get("mastodon_uri", "")


def log_publish(meta: dict, article_id: str, push_id: str, kit_id: str,
                bsky_uri: str, mastodon_uri: str):
    STATE.mkdir(exist_ok=True)
    line = " | ".join([
        datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        article_id,
        meta["title"],
        "premium" if meta.get("premium") else "free",
        push_id,
        kit_id,
        bsky_uri,
        mastodon_uri,
    ])
    with PUBLISH_LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: weekly_publish.py <article_id>")
    article_id = sys.argv[1]

    print(f"=== Publishing {article_id} ===")
    meta, body, hero = parse_draft(article_id)
    print(f"Title: {meta['title']}")
    print(f"Premium: {meta.get('premium', False)}")

    copy_assets(article_id, body, hero)
    update_manifest(meta, article_id)

    push_id = send_push(meta["push_title"], meta["push_body"], article_id)
    kit_id = schedule_kit_newsletter(meta, body, article_id)
    bsky_uri, mastodon_uri = post_social(article_id)

    log_publish(meta, article_id, push_id, kit_id, bsky_uri, mastodon_uri)

    print("=== Publish complete ===")
    print(f"Push: {push_id}")
    print(f"Kit broadcast: {kit_id}")
    print(f"Bluesky: {bsky_uri}")
    print(f"Mastodon: {mastodon_uri}")


if __name__ == "__main__":
    main()
