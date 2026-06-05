#!/usr/bin/env python3
"""Generate the Week Ahead newsletter draft for the upcoming week.

Reads state/week_ahead_events.json — a list of {date, title, source_url, kind}.
Picks events whose ISO date falls in the upcoming Mon–Sun window.
Writes a draft markdown file to /tmp/week_ahead_draft.md with frontmatter
(subject, preview, send_at) plus a skeleton body for the agent to fill in.

Prints JSON to stdout: {draft_path, week_start, week_end, events_count, subject, send_at}
"""
from __future__ import annotations
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = REPO_ROOT / "state"
EVENTS = STATE_DIR / "week_ahead_events.json"
DRAFT_OUT = Path("/tmp/week_ahead_draft.md")


def upcoming_window(now: datetime) -> tuple[datetime, datetime]:
    """Return (sunday_start, saturday_end) for the upcoming Sun–Sat week.

    Run on Friday: 'upcoming' = next Sunday through the following Saturday.
    """
    # weekday: Monday=0 … Sunday=6
    days_until_sunday = (6 - now.weekday()) % 7
    if days_until_sunday == 0:
        days_until_sunday = 7
    sunday = (now + timedelta(days=days_until_sunday)).replace(hour=0, minute=0, second=0, microsecond=0)
    saturday = sunday + timedelta(days=7) - timedelta(seconds=1)
    return sunday, saturday


def load_events() -> list[dict]:
    if not EVENTS.exists():
        return []
    return json.loads(EVENTS.read_text(encoding="utf-8"))


def filter_events(events: list[dict], start: datetime, end: datetime) -> list[dict]:
    out = []
    for e in events:
        try:
            d = datetime.fromisoformat(e["date"]).replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if start <= d <= end:
            out.append(e)
    out.sort(key=lambda e: e["date"])
    return out


def build_draft(start: datetime, end: datetime, events: list[dict]) -> tuple[str, dict]:
    subject = f"Week Ahead: {start.strftime('%b %-d')}–{end.strftime('%b %-d')}"
    preview = "What to watch in Artemis, Starship, and the broader Moon push this week."
    send_at = start.replace(hour=7, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")

    items_md = ""
    if events:
        for e in events:
            d = datetime.fromisoformat(e["date"]).strftime("%a %b %-d")
            link = f" [{e.get('source','source')}]({e['source_url']})" if e.get("source_url") else ""
            items_md += f"- **{d}** — {e['title']}{link}\n"
    else:
        items_md = "- [REPLACE: no confirmed events yet, fill in from this week's research]\n"

    body = f"""---
subject: {subject}
preview: {preview}
send_at: {send_at}
---

# Week Ahead

[REPLACE: opener — 1-2 honest sentences. If quiet, say so.]

## What to watch for

{items_md}

## In the app this week

[REPLACE: tease the topic in one sentence]

---

Want more? The Wednesday Briefing is the long-form deep dive. [Subscribe](https://artemis-briefing.kit.com).
"""
    meta = {
        "subject": subject,
        "preview": preview,
        "send_at": send_at,
        "events_count": len(events),
        "week_start": start.date().isoformat(),
        "week_end": end.date().isoformat(),
    }
    return body, meta


def main():
    now = datetime.now(timezone.utc)
    start, end = upcoming_window(now)
    events = load_events()
    in_window = filter_events(events, start, end)

    body, meta = build_draft(start, end, in_window)
    DRAFT_OUT.write_text(body, encoding="utf-8")
    meta["draft_path"] = str(DRAFT_OUT)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
