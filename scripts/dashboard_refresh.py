#!/usr/bin/env python3
"""
Dashboard refresh: fetch all sources via dashboard_sources, render Dashboard 2.0,
write dashboard/index.html. The GitHub Actions workflow does the git commit/push.

Reads credentials from env-vars (see scripts/dashboard_sources.py).
Soft-fails on any single source so the dashboard always renders.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
DASHBOARD_DIR = REPO_ROOT / "dashboard"
STATE_DIR = REPO_ROOT / "state"
LOG = STATE_DIR / "dashboard_refresh_log.txt"

# Make sources importable
sys.path.insert(0, str(SCRIPTS))


def log(line: str):
    STATE_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    with LOG.open("a", encoding="utf-8") as f:
        f.write(f"{stamp} | {line}\n")
    print(line, file=sys.stderr)


def main():
    log("dashboard_refresh 2.0 start")

    try:
        import dashboard_sources
    except Exception as e:
        log(f"FATAL: cannot import dashboard_sources: {e}")
        traceback.print_exc()
        sys.exit(1)

    try:
        data = dashboard_sources.fetch_all()
    except Exception as e:
        log(f"FATAL: fetch_all crashed: {type(e).__name__}: {e}")
        traceback.print_exc()
        sys.exit(1)

    # Log each source's status
    for key in ("ga4", "kit", "asc", "bluesky", "mastodon", "threads",
                "instagram", "push", "roadmap", "targets"):
        s = data.get(key, {})
        st = s.get("status", "?")
        extra = ""
        if key == "ga4" and st == "ok":
            extra = f" | latest={s.get('latest', {}).get('active')} 28d={s.get('total_active_28d')}"
        if key == "kit" and st == "ok":
            extra = f" | active={s.get('active_subscribers')}"
        if key == "bluesky" and st == "ok":
            extra = f" | followers={s.get('followers')}"
        if key == "mastodon" and st == "ok":
            extra = f" | followers={s.get('followers')}"
        if key == "asc" and st == "ok":
            extra = f" | reviews={s.get('reviews_count_recent')} avg={s.get('avg_rating_recent')}"
        if st in ("error", "skipped", "blocked"):
            reason = s.get('error') or s.get('reason') or ''
            extra = f" | {reason[:120]}"
        log(f"  {key}: {st}{extra}")

    # Render
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    data_path = DASHBOARD_DIR / "data.json"
    data_path.write_text(json.dumps(data, indent=2, default=str))
    log(f"wrote {data_path.name} ({data_path.stat().st_size} bytes)")

    try:
        import dashboard_render
        html_out = dashboard_render.render_page(data)
    except Exception as e:
        log(f"FATAL: render crashed: {type(e).__name__}: {e}")
        traceback.print_exc()
        sys.exit(1)

    out_path = DASHBOARD_DIR / "index.html"
    out_path.write_text(html_out)
    log(f"wrote {out_path.name} ({out_path.stat().st_size} bytes)")
    log("dashboard_refresh 2.0 done")


if __name__ == "__main__":
    main()
