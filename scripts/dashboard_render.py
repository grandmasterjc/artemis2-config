#!/usr/bin/env python3
"""Render the Artemis Tracker dashboard HTML.

Writes /tmp/dashboard.html, ready to be copied into dashboard/index.html
in the repo.
"""
from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dashboard_data import collect_all

OUT = Path("/tmp/dashboard.html")

CSS = """
body { margin:0; background:#0b1020; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; color:#e6e9f5; }
.wrap { max-width:980px; margin:0 auto; padding:32px 24px; }
h1 { color:#fff; }
h2 { color:#fff; margin-top:36px; border-bottom:1px solid #2a3050; padding-bottom:6px; }
.grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:16px; margin:20px 0; }
.card { background:#161c34; border-radius:10px; padding:16px; }
.card .label { color:#9aa3c0; font-size:13px; text-transform:uppercase; letter-spacing:0.5px; }
.card .value { color:#fff; font-size:28px; font-weight:600; margin-top:6px; }
table { width:100%; border-collapse:collapse; margin-top:12px; font-size:14px; }
th, td { padding:8px 10px; text-align:left; border-bottom:1px solid #2a3050; }
th { color:#9aa3c0; font-weight:500; }
.foot { color:#7c84a0; margin-top:32px; font-size:13px; }
"""


def _safe(d: dict, *keys, default=""):
    cur = d
    for k in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
        if cur is None:
            return default
    return cur


def render(data: dict) -> str:
    ga4 = data.get("ga4", {})
    kit = data.get("kit", {})
    asc = data.get("asc", {})

    active_users = _safe(ga4, "daily_users")
    last_day_active = active_users[-1]["active"] if isinstance(active_users, list) and active_users else "—"

    cards = [
        ("Daily Active (latest)", last_day_active),
        ("Total Notif Opens (30d)", ga4.get("total_notification_open", "—")),
        ("Notif Open Users (30d)", ga4.get("total_notification_open_users", "—")),
        ("Notif Foreground (30d)", ga4.get("total_notification_foreground", "—")),
        ("Kit Subscribers", kit.get("active_subscribers", "—")),
        ("App Installs (lifetime)", asc.get("units_lifetime", "—")),
        ("Pushes Sent (total)", data.get("push_total", 0)),
    ]
    cards_html = "".join(
        f'<div class="card"><div class="label">{label}</div><div class="value">{value}</div></div>'
        for label, value in cards
    )

    rows = data.get("push_history", [])
    table_html = ""
    if rows:
        table_html = "<table><thead><tr><th>Sent (UTC)</th><th>Title</th><th>Article</th></tr></thead><tbody>"
        for r in reversed(rows):
            ts = r.get("timestamp_utc", "")[:16].replace("T", " ")
            table_html += f"<tr><td>{ts}</td><td>{r.get('title','')}</td><td>{r.get('article_id','')}</td></tr>"
        table_html += "</tbody></table>"

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Artemis Tracker — Dashboard</title>
<style>{CSS}</style>
</head><body><div class="wrap">
<h1>Artemis Tracker — Dashboard</h1>
<p style="color:#9aa3c0">Generated {data.get('generated_at','')}</p>

<h2>Overview</h2>
<div class="grid">{cards_html}</div>

<h2>Recent push notifications</h2>
{table_html or '<p style="color:#9aa3c0">No push history yet.</p>'}

<div class="foot">Auto-refreshed daily from GA4, Kit and App Store Connect.</div>
</div></body></html>
"""


def main():
    data = collect_all()
    OUT.write_text(render(data), encoding="utf-8")
    print(str(OUT))


if __name__ == "__main__":
    main()
