#!/usr/bin/env python3
"""
Orchestrates the weekly Artemis Tracker publish flow.

Reads a draft from drafts/{article_id}/article_draft.md (+ hero.jpg), then:
1. Copies hero to updates/images/{article_id}.jpg
2. Writes article body to updates/articles/{article_id}.md
3. Inserts new entry at top of updates/manifest.json
4. (workflow commits + pushes here)
5. Polls GitHub Pages until the new article is live
6. Sends FCM push
7. Schedules Kit newsletter for tonight 21:30 CEST
8. Posts thread to Bluesky + Mastodon
9. Appends to state/publish_history.txt

Phases (so the workflow can commit between them):
  --phase=prepare  steps 1-3, then exit (workflow commits + pushes)
  --phase=announce steps 5-9 (poll Pages, then push/newsletter/social)
  --phase=full     legacy single-pass, kept for local testing only
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
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
PENDING_FILE = STATE / ".pending_publish.json"

PAGES_MANIFEST_URL = "https://grandmasterjc.github.io/artemis2-config/updates/manifest.json"

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


def wait_for_pages(article_id: str, timeout_s: int = 600, interval_s: int = 15) -> None:
    """Poll GitHub Pages until the new manifest entry is served.

    GitHub Pages deploys typically land within 30-90 s after a push,
    but can take longer. We keep the push notification blocked until
    the article is actually visible to the app, otherwise users would
    tap the push and see a 'not found' state.
    """
    deadline = time.time() + timeout_s
    attempt = 0
    article_url = (
        f"https://grandmasterjc.github.io/artemis2-config/updates/articles/{article_id}.md"
    )
    while time.time() < deadline:
        attempt += 1
        try:
            req = urllib.request.Request(
                PAGES_MANIFEST_URL,
                headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            ids = [u.get("id") for u in payload.get("updates", [])]
            if article_id in ids:
                try:
                    with urllib.request.urlopen(article_url, timeout=10) as r:
                        if r.status == 200:
                            print(
                                f"pages: manifest + body live for {article_id} "
                                f"(attempt {attempt})"
                            )
                            return
                except Exception as e:  # noqa: BLE001
                    print(f"pages: manifest live but body not ready: {e}")
            else:
                top = ids[0] if ids else "empty"
                print(
                    f"pages: attempt {attempt} - {article_id} not in manifest yet "
                    f"(top: {top})"
                )
        except Exception as e:  # noqa: BLE001
            print(f"pages: attempt {attempt} fetch error: {e}")
        time.sleep(interval_s)
    raise SystemExit(
        f"Timed out after {timeout_s}s waiting for Pages to serve {article_id}. "
        "Aborting push so users don't tap a dead link."
    )


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
    # social_publish.py emits json.dumps(result, indent=2) -- a multi-line
    # JSON object. Parse the whole stdout, not just the last line.
    try:
        result = json.loads(out)
    except json.JSONDecodeError:
        # Fall back to extracting the JSON object from stdout in case there
        # were any preceding log lines.
        start = out.find("{")
        end = out.rfind("}")
        if start == -1 or end == -1:
            print(f"warning: could not parse social_publish output: {out!r}")
            return "", ""
        result = json.loads(out[start:end + 1])
    if not result.get("bluesky_ok"):
        print(f"warning: bluesky failed: {result.get('bluesky_error', '')}")
    if not result.get("mastodon_ok"):
        print(f"warning: mastodon failed: {result.get('mastodon_error', '')}")
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


def phase_prepare(article_id: str) -> None:
    print(f"=== Phase: prepare ({article_id}) ===")
    meta, body, hero = parse_draft(article_id)
    print(f"Title: {meta['title']}")
    print(f"Premium: {meta.get('premium', False)}")

    copy_assets(article_id, body, hero)
    update_manifest(meta, article_id)

    STATE.mkdir(exist_ok=True)
    PENDING_FILE.write_text(json.dumps({
        "article_id": article_id,
        "meta": meta,
        "body": body,
    }), encoding="utf-8")
    print(f"prepare: wrote {PENDING_FILE.name} - ready for commit + push")


def phase_announce(article_id: str) -> None:
    print(f"=== Phase: announce ({article_id}) ===")
    if PENDING_FILE.exists():
        pending = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
        if pending.get("article_id") != article_id:
            raise SystemExit(
                f"Pending file is for {pending.get('article_id')}, not {article_id}"
            )
        meta = pending["meta"]
        body = pending["body"]
    else:
        meta, body, _hero = parse_draft(article_id)

    wait_for_pages(article_id)

    push_id = send_push(meta["push_title"], meta["push_body"], article_id)
    kit_id = schedule_kit_newsletter(meta, body, article_id)
    bsky_uri, mastodon_uri = post_social(article_id)

    log_publish(meta, article_id, push_id, kit_id, bsky_uri, mastodon_uri)

    try:
        PENDING_FILE.unlink()
    except FileNotFoundError:
        pass

    print("=== Announce complete ===")
    print(f"Push: {push_id}")
    print(f"Kit broadcast: {kit_id}")
    print(f"Bluesky: {bsky_uri}")
    print(f"Mastodon: {mastodon_uri}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("article_id")
    parser.add_argument(
        "--phase",
        choices=["prepare", "announce", "full"],
        default="full",
        help=(
            "prepare = stage assets + manifest then exit (workflow commits next); "
            "announce = poll Pages then push/newsletter/social; "
            "full = both back-to-back (local testing only)."
        ),
    )
    args = parser.parse_args()

    if args.phase == "prepare":
        phase_prepare(args.article_id)
    elif args.phase == "announce":
        phase_announce(args.article_id)
    else:
        phase_prepare(args.article_id)
        phase_announce(args.article_id)


if __name__ == "__main__":
    main()
