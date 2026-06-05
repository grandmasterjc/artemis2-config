#!/usr/bin/env python3
"""Post a thread to Bluesky and Mastodon for an Artemis Tracker article.

Usage:
    python3 scripts/social_publish.py <article_draft.md> <hero_image_url>

Reads the article frontmatter (title, subtitle) and produces a 2–3 post thread.
The first post embeds the hero image; subsequent posts continue the thread.

Returns JSON on stdout:
  {"bluesky_ok": bool, "mastodon_ok": bool,
   "bluesky_uri": "at://...", "mastodon_uri": "https://...",
   "bluesky_error": "...", "mastodon_error": "..."}

Logs every run to state/social_post_history.csv.
"""
from __future__ import annotations

import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = REPO_ROOT / "state"
LOG = STATE_DIR / "social_post_history.csv"
WORKSPACE = Path("/home/user/workspace")

BLUESKY_CFG = WORKSPACE / "bluesky_config.json"
MASTODON_CFG = WORKSPACE / "mastodon_config.json"


def parse_frontmatter(md_path: Path) -> tuple[dict, str]:
    text = md_path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    fm = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, parts[2].lstrip()


def first_sentences(body: str, n: int = 2) -> str:
    paras = [p.strip() for p in body.split("\n\n") if p.strip() and not p.lstrip().startswith(("#", "!", "---"))]
    if not paras:
        return ""
    text = paras[0]
    sentences = text.replace("\n", " ").split(". ")
    return ". ".join(sentences[:n]).strip().rstrip(".") + "."


# ---------- Bluesky ----------

def bluesky_login(handle: str, app_password: str) -> dict:
    r = requests.post(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        json={"identifier": handle, "password": app_password},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def bluesky_upload_image(session: dict, image_bytes: bytes, mime: str = "image/jpeg") -> dict:
    r = requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
        headers={"Authorization": f"Bearer {session['accessJwt']}", "Content-Type": mime},
        data=image_bytes,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["blob"]


def bluesky_create_post(session: dict, text: str, *, reply=None, embed=None) -> dict:
    record = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if reply:
        record["reply"] = reply
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


def post_to_bluesky(title: str, subtitle: str, body: str, article_url: str, hero_url: str) -> tuple[str, str]:
    cfg = json.loads(BLUESKY_CFG.read_text())
    session = bluesky_login(cfg["handle"], cfg["app_password"])

    img_bytes = requests.get(hero_url, timeout=30).content
    blob = bluesky_upload_image(session, img_bytes)
    embed = {
        "$type": "app.bsky.embed.images",
        "images": [{"alt": title, "image": blob}],
    }

    head_text = (title + ("\n\n" + subtitle if subtitle else ""))[:280]
    head = bluesky_create_post(session, head_text, embed=embed)
    root_ref = {"uri": head["uri"], "cid": head["cid"]}

    second_text = first_sentences(body, 2)[:280]
    if second_text:
        bluesky_create_post(
            session,
            second_text,
            reply={"root": root_ref, "parent": root_ref},
        )

    closer = f"Read the full piece in the app: {article_url}"[:280]
    bluesky_create_post(
        session,
        closer,
        reply={"root": root_ref, "parent": root_ref},
    )
    return head["uri"], head["uri"]


# ---------- Mastodon ----------

def mastodon_upload_image(base_url: str, token: str, image_bytes: bytes) -> str:
    r = requests.post(
        f"{base_url}/api/v2/media",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("hero.jpg", image_bytes, "image/jpeg")},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["id"]


def mastodon_post(base_url: str, token: str, status: str, *, media_ids=None, in_reply_to=None) -> dict:
    payload = {"status": status, "visibility": "public"}
    if media_ids:
        payload["media_ids[]"] = media_ids
    if in_reply_to:
        payload["in_reply_to_id"] = in_reply_to
    r = requests.post(
        f"{base_url}/api/v1/statuses",
        headers={"Authorization": f"Bearer {token}"},
        data=payload,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def post_to_mastodon(title: str, subtitle: str, body: str, article_url: str, hero_url: str) -> tuple[str, str]:
    cfg = json.loads(MASTODON_CFG.read_text())
    base_url = cfg["base_url"].rstrip("/")
    token = cfg["access_token"]

    img_bytes = requests.get(hero_url, timeout=30).content
    media_id = mastodon_upload_image(base_url, token, img_bytes)

    # Mastodon media uploads need a moment to finish processing
    time.sleep(2)

    head_text = title + ("\n\n" + subtitle if subtitle else "")
    head = mastodon_post(base_url, token, head_text[:480], media_ids=[media_id])

    second = first_sentences(body, 2)
    if second:
        mastodon_post(base_url, token, second[:480], in_reply_to=head["id"])

    mastodon_post(base_url, token, f"Read the full piece in the app: {article_url}", in_reply_to=head["id"])

    return head["url"], head["url"]


# ---------- main ----------

def log_run(article_id: str, result: dict):
    STATE_DIR.mkdir(exist_ok=True)
    new = not LOG.exists()
    with LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp_utc", "article_id", "bluesky_ok", "mastodon_ok", "bluesky_uri", "mastodon_uri", "bluesky_error", "mastodon_error"])
        w.writerow([
            datetime.now(timezone.utc).isoformat(),
            article_id,
            result["bluesky_ok"],
            result["mastodon_ok"],
            result.get("bluesky_uri", ""),
            result.get("mastodon_uri", ""),
            result.get("bluesky_error", ""),
            result.get("mastodon_error", ""),
        ])


def main():
    if len(sys.argv) < 3:
        print("Usage: social_publish.py <article_draft.md> <hero_image_url>", file=sys.stderr)
        sys.exit(2)
    md_path = Path(sys.argv[1])
    hero_url = sys.argv[2]
    fm, body = parse_frontmatter(md_path)
    article_id = fm.get("id", md_path.stem)
    title = fm.get("title", "")
    subtitle = fm.get("subtitle", "")
    article_url = f"https://artemistracker.app/u/{article_id}"

    result = {"bluesky_ok": False, "mastodon_ok": False}

    try:
        uri, perma = post_to_bluesky(title, subtitle, body, article_url, hero_url)
        result["bluesky_ok"] = True
        result["bluesky_uri"] = uri
    except Exception as e:
        result["bluesky_error"] = f"{type(e).__name__}: {e}"

    try:
        uri, perma = post_to_mastodon(title, subtitle, body, article_url, hero_url)
        result["mastodon_ok"] = True
        result["mastodon_uri"] = uri
    except Exception as e:
        result["mastodon_error"] = f"{type(e).__name__}: {e}"

    log_run(article_id, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
