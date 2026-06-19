"""
Append a row to state/subscribers_history.csv each time the dashboard refreshes.

Columns: date (UTC YYYY-MM-DD), kit_active, plus_active, ios_active, play_active, total

Idempotent: if a row already exists for today's date, it is updated in place
instead of appended. This means multiple refreshes per day will overwrite the
same row, and only the latest snapshot of the day is kept.

Loads from data dict produced by dashboard_sources.fetch_all().
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HISTORY_CSV = REPO_ROOT / "state" / "subscribers_history.csv"

FIELDS = ["date", "kit_active", "plus_active", "ios_active", "play_active", "total"]


def _compute_plus(data: dict) -> tuple[int | None, int | None, int | None]:
    """Return (ios_active, play_active, plus_total). None if data missing."""
    asc = data.get("asc", {}) or {}
    play = data.get("play", {}) or {}

    ios_subs = asc.get("subscriptions") or {} if isinstance(asc, dict) else {}
    ios_active = ios_subs.get("active_subscribers") if ios_subs.get("status") == "ok" else None

    play_active = None
    if play.get("status") == "ok":
        play_new = play.get("new_subscribers_30d") or 0
        play_events = play.get("by_event_type") or {}
        play_cancels = sum(v for k, v in play_events.items() if "cancel" in k.lower())
        play_active = max(0, play_new - play_cancels)

    plus_total = None
    if ios_active is not None or play_active is not None:
        plus_total = (ios_active or 0) + (play_active or 0)

    return ios_active, play_active, plus_total


def append_snapshot(data: dict) -> dict | None:
    """Append (or upsert) today's row in subscribers_history.csv.

    Returns the row dict that was written, or None if no useful data was
    available (all fields None).
    """
    kit = data.get("kit", {}) or {}
    kit_active = kit.get("active_subscribers") if kit.get("status") == "ok" else None

    ios_active, play_active, plus_total = _compute_plus(data)

    # Nothing useful — skip
    if kit_active is None and plus_total is None:
        return None

    today = datetime.now(timezone.utc).date().isoformat()
    total = (kit_active or 0) + (plus_total or 0)

    row = {
        "date": today,
        "kit_active": kit_active if kit_active is not None else "",
        "plus_active": plus_total if plus_total is not None else "",
        "ios_active": ios_active if ios_active is not None else "",
        "play_active": play_active if play_active is not None else "",
        "total": total,
    }

    HISTORY_CSV.parent.mkdir(parents=True, exist_ok=True)

    # Read existing rows, upsert by date
    rows: list[dict] = []
    if HISTORY_CSV.exists():
        with HISTORY_CSV.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                if r.get("date") != today:
                    rows.append(r)

    rows.append(row)
    rows.sort(key=lambda r: r["date"])

    with HISTORY_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    return row


def load_history(limit_days: int | None = None) -> list[dict]:
    """Return list of rows sorted by date ascending. Casts numeric fields to int."""
    if not HISTORY_CSV.exists():
        return []
    rows: list[dict] = []
    with HISTORY_CSV.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            parsed = {"date": r.get("date", "")}
            for k in ("kit_active", "plus_active", "ios_active", "play_active", "total"):
                v = r.get(k, "")
                try:
                    parsed[k] = int(v) if v != "" else None
                except (ValueError, TypeError):
                    parsed[k] = None
            rows.append(parsed)
    rows.sort(key=lambda r: r["date"])
    if limit_days:
        rows = rows[-limit_days:]
    return rows
