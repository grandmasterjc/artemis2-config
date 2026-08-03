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
from _creds import load_bluesky, load_mastodon, load_threads

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
    cfg = load_bluesky()
    session = bluesky_login(cfg["handle"], cfg["password"])

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
    cfg = load_mastodon()
    base_url = cfg.get("base_url") or f"https://{cfg['instance']}"
    base_url = base_url.rstrip("/")
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


# ---------- Threads ----------

THREADS_API = "https://graph.threads.net/v1.0"


def threads_create_container(user_id: str, token: str, *, text: str, media_type: str = "TEXT",
                             image_url: str | None = None, reply_to_id: str | None = None) -> str:
    payload = {
        "media_type": media_type,
        "text": text,
        "access_token": token,
    }
    if media_type == "IMAGE" and image_url:
        payload["image_url"] = image_url
    if reply_to_id:
        payload["reply_to_id"] = reply_to_id
    r = requests.post(f"{THREADS_API}/{user_id}/threads", data=payload, timeout=30)
    r.raise_for_status()
    return r.json()["id"]


def threads_publish(user_id: str, token: str, creation_id: str) -> str:
    # threads_publish intermittently returns 500 even when the container is
    # fine (hit us 2026-06-24, 07-08 and 07-24, killing the post each time).
    # Retry with backoff; a container stays publishable for 24h so waiting
    # out a transient server error is always the right call.
    last_error: Exception | None = None
    for attempt, delay in enumerate((0, 15, 45, 90), start=1):
        if delay:
            time.sleep(delay)
        r = requests.post(
            f"{THREADS_API}/{user_id}/threads_publish",
            data={"creation_id": creation_id, "access_token": token},
            timeout=30,
        )
        if r.status_code < 500:
            r.raise_for_status()
            return r.json()["id"]
        last_error = requests.HTTPError(
            f"{r.status_code} Server Error after {attempt} attempt(s) for url: {r.url}"
        )
    raise last_error


def threads_permalink(token: str, post_id: str) -> str:
    try:
        r = requests.get(
            f"{THREADS_API}/{post_id}",
            params={"fields": "permalink", "access_token": token},
            timeout=30,
        )
        if r.status_code != 200:
            return ""
        return r.json().get("permalink", "")
    except Exception:
        return ""


def post_to_threads(title: str, subtitle: str, body: str, article_url: str, hero_url: str) -> tuple[str, str]:
    cfg = load_threads()
    user_id = cfg["user_id"]
    token = cfg["access_token"]

    head_text = (title + (("\n\n" + subtitle) if subtitle else ""))[:480]

    head_container = threads_create_container(
        user_id, token, text=head_text, media_type="IMAGE", image_url=hero_url
    )
    time.sleep(8)
    head_id = threads_publish(user_id, token, head_container)

    second = first_sentences(body, 2)
    if second:
        reply_container = threads_create_container(
            user_id, token, text=second[:480], media_type="TEXT", reply_to_id=head_id
        )
        time.sleep(2)
        threads_publish(user_id, token, reply_container)

    cta_container = threads_create_container(
        user_id, token,
        text=f"Read the full piece in the app: {article_url}"[:480],
        media_type="TEXT",
        reply_to_id=head_id,
    )
    time.sleep(2)
    threads_publish(user_id, token, cta_container)

    permalink = threads_permalink(token, head_id) or f"threads:{head_id}"
    return head_id, permalink


# ---------- main ----------

def log_run(article_id: str, result: dict):
    STATE_DIR.mkdir(exist_ok=True)
    new = not LOG.exists()
    with LOG.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow([
                "timestamp_utc", "article_id",
                "bluesky_ok", "mastodon_ok", "threads_ok",
                "bluesky_uri", "mastodon_uri", "threads_uri",
                "bluesky_error", "mastodon_error", "threads_error",
            ])
        w.writerow([
            datetime.now(timezone.utc).isoformat(),
            article_id,
            result.get("bluesky_ok", False),
            result.get("mastodon_ok", False),
            result.get("threads_ok", False),
            result.get("bluesky_uri", ""),
            result.get("mastodon_uri", ""),
            result.get("threads_uri", ""),
            result.get("bluesky_error", ""),
            result.get("mastodon_error", ""),
            result.get("threads_error", ""),
        ])


def main():
    # Optional: --channels=threads (comma-separated subset of
    # bluesky,mastodon,threads). Used to recover a single failed channel
    # without duplicating posts on the ones that succeeded.
    args = [a for a in sys.argv[1:] if not a.startswith("--channels=")]
    channels = {"bluesky", "mastodon", "threads"}
    explicit_channels = False
    for a in sys.argv[1:]:
        if a.startswith("--channels="):
            channels = {c.strip() for c in a.split("=", 1)[1].split(",") if c.strip()}
            explicit_channels = True

    if len(args) < 2:
        print("Usage: social_publish.py <article_draft.md> <hero_image_url> [--channels=bluesky,mastodon,threads]", file=sys.stderr)
        sys.exit(2)
    md_path = Path(args[0])
    hero_url = args[1]
    fm, body = parse_frontmatter(md_path)
    article_id = fm.get("id", md_path.stem)
    title = fm.get("title", "")
    subtitle = fm.get("subtitle", "")
    article_url = f"https://artemistracker.app/u/{article_id}"

    def tagged(channel: str) -> str:
        """Per-channel source tag, so analytics can tell the channels apart."""
        return f"{article_url}?ref={channel}"

    result = {"bluesky_ok": False, "mastodon_ok": False, "threads_ok": False}

    if "bluesky" in channels:
        try:
            uri, perma = post_to_bluesky(title, subtitle, body, tagged("bluesky"), hero_url)
            result["bluesky_ok"] = True
            result["bluesky_uri"] = uri
        except Exception as e:
            result["bluesky_error"] = f"{type(e).__name__}: {e}"

    if "mastodon" in channels:
        try:
            uri, perma = post_to_mastodon(title, subtitle, body, tagged("mastodon"), hero_url)
            result["mastodon_ok"] = True
            result["mastodon_uri"] = uri
        except Exception as e:
            result["mastodon_error"] = f"{type(e).__name__}: {e}"

    if "threads" not in channels:
        pass
    else:
        _post_threads(result, title, subtitle, body, tagged("threads"), hero_url)

    log_run(article_id, result)
    print(json.dumps(result, indent=2))
    # In recovery mode (--channels given): fail the step loudly when a
    # requested channel produced no post. Full runs keep exit 0 because
    # weekly_publish.py invokes this mid-announce via check_output and must
    # finish its own logging even when one channel fails.
    failed = [c for c in channels if not result.get(f"{c}_ok")]
    if failed and explicit_channels:
        print(f"FAILED channels: {', '.join(sorted(failed))}", file=sys.stderr)
        sys.exit(1)


def _post_threads(result, title, subtitle, body, article_url, hero_url):
    try:
        post_id, perma = post_to_threads(title, subtitle, body, article_url, hero_url)
        result["threads_ok"] = True
        result["threads_uri"] = perma or post_id
    except Exception as e:
        result["threads_error"] = f"{type(e).__name__}: {e}"


if __name__ == "__main__":
    main()
