#!/usr/bin/env python3
"""
Publish the Week Ahead newsletter as a Kit broadcast.

Reads a draft markdown file with a frontmatter (subject, preview) and posts
it to Kit /v4/broadcasts. Defaults to scheduling for tonight 18:00 CEST, or
sends now with --now.

The Week Ahead is free for all subscribers — no app gating, no merch insert.

Usage:
  python scripts/publish_week_ahead.py --draft /tmp/week_ahead_draft.md
  python scripts/publish_week_ahead.py --draft path.md --now
  python scripts/publish_week_ahead.py --draft path.md --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from _creds import load_kit  # noqa: E402
from kit_template import build_newsletter_html  # noqa: E402


def parse_draft(path: Path) -> tuple[dict, str]:
    """Return (frontmatter, body). Frontmatter delimited by --- ... ---."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError("Draft must start with YAML frontmatter (---)")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Could not parse frontmatter (need two --- delimiters)")
    fm_text = parts[1].strip()
    body = parts[2].strip()

    # Tiny YAML parser — only key: "value" or key: value
    fm = {}
    for line in fm_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        if v.startswith('"') and v.endswith('"'):
            v = v[1:-1]
        fm[k.strip()] = v
    return fm, body


def schedule_or_send(api_key: str, subject: str, preview: str, html: str,
                     send_at_utc: datetime | None) -> str:
    payload = {
        "subject": subject,
        "content": html,
        "description": preview[:140],
        "preview_text": preview[:140],
        "public": True,
    }
    if send_at_utc is not None:
        payload["send_at"] = send_at_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    req = urllib.request.Request(
        "https://api.kit.com/v4/broadcasts",
        data=json.dumps(payload).encode(),
        headers={"X-Kit-Api-Key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    resp = urllib.request.urlopen(req, timeout=60)
    result = json.loads(resp.read())
    bid = result.get("broadcast", {}).get("id") or result.get("id")
    return str(bid)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", required=True, help="Path to week ahead markdown draft")
    ap.add_argument("--now", action="store_true", help="Send immediately instead of scheduling")
    ap.add_argument("--at", help="ISO UTC timestamp to schedule at (overrides default)")
    ap.add_argument("--dry-run", action="store_true", help="Print payload, don't post")
    args = ap.parse_args()

    fm, body = parse_draft(Path(args.draft))
    subject = fm.get("subject", "Week Ahead")
    preview = fm.get("preview", subject)

    # No hero for Week Ahead — pass empty string; template still renders fine.
    # We hide the empty <img> via inline style.
    html = build_newsletter_html(
        hero_image_url="",
        hero_alt="",
        body_markdown=body,
        include_week_ahead_cta=False,
    )
    # Remove the empty hero img to avoid broken-image icon
    html = html.replace('<div class="hero"><img src="" alt=""></div>', "")

    # Schedule timing
    send_at_utc: datetime | None
    if args.now:
        send_at_utc = None  # send immediately
    elif args.at:
        send_at_utc = datetime.fromisoformat(args.at.replace("Z", "+00:00")).astimezone(timezone.utc)
    else:
        # Default: tonight 18:00 CEST = 16:00 UTC
        now = datetime.now(timezone.utc)
        today_1800_cest = now.replace(hour=16, minute=0, second=0, microsecond=0)
        send_at_utc = today_1800_cest
        if send_at_utc < now + timedelta(minutes=10):
            send_at_utc = now + timedelta(minutes=10)

    if args.dry_run:
        print("=== DRY RUN ===")
        print(f"Subject: {subject}")
        print(f"Preview: {preview}")
        print(f"Send at: {send_at_utc.isoformat() if send_at_utc else 'NOW'}")
        print(f"HTML length: {len(html)} bytes")
        print("--- HTML preview (first 800 chars) ---")
        print(html[:800])
        return

    cfg = load_kit()
    bid = schedule_or_send(cfg["api_key"], subject, preview, html, send_at_utc)
    when = send_at_utc.isoformat() if send_at_utc else "immediately"
    print(f"Kit broadcast: {bid} (send: {when})")


if __name__ == "__main__":
    main()
