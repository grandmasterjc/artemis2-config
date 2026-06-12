"""Collect data for the Artemis Tracker dashboard.

Pulls from:
- state/push_history.csv (committed)
- /home/user/workspace/dashboard_ga4_cache.json (refreshed by cron before render)
- /home/user/workspace/kit_subscriber_cache.json (optional, refreshed by cron)
- /home/user/workspace/asc_cache.json (App Store Connect, optional)

Returns a single dict that dashboard_render.py turns into HTML.
"""
from __future__ import annotations
import csv
import json
import os
from pathlib import Path
from datetime import datetime, timezone

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = REPO_ROOT / "state"
PUSH_HISTORY = STATE_DIR / "push_history.csv"
WORKSPACE = Path(os.environ.get("ARTEMIS_WORKSPACE", "/home/user/workspace"))


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_push_history() -> list[dict]:
    if not PUSH_HISTORY.exists():
        return []
    rows = []
    with PUSH_HISTORY.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def collect_all() -> dict:
    ga4 = _load_json(WORKSPACE / "dashboard_ga4_cache.json", {})
    kit = _load_json(WORKSPACE / "kit_subscriber_cache.json", {})
    asc = _load_json(WORKSPACE / "asc_cache.json", {})

    push_rows = load_push_history()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ga4": ga4,
        "kit": kit,
        "asc": asc,
        "push_history": push_rows[-30:],  # last 30 pushes
        "push_total": len(push_rows),
    }
