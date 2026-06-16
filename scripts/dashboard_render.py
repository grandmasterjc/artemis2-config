#!/usr/bin/env python3
"""
Dashboard 2.0 renderer for Artemis Tracker.

Reads data from dashboard_sources.fetch_all() (which calls all sources fresh,
or you can pass a cached JSON file via --data PATH).

Produces a single static HTML file at dashboard/index.html with:
  - North Star KPI (DAU vs 500 by Aug 31, 2026)
  - Supporting KPI cards with goal lines
  - DAU chart 90d with target line
  - Newsletter (Kit) section
  - Social cards (Bluesky, Mastodon, Threads/Instagram blocked notice)
  - App Store reviews section
  - Roadmap section (in_progress, upcoming, blocked, completed)
  - Push history table
  - Top countries
  - Health / source-status footer

Design: nøkternt, dark theme, no clickbait. Inline CSS + minimal SVG charts —
no external JS or fonts so it loads even offline.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_DIR = REPO_ROOT / "dashboard"
DATA_CACHE = DASHBOARD_DIR / "data.json"

# Make sources importable
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def esc(s) -> str:
    if s is None:
        return ""
    return html.escape(str(s), quote=True)


def fmt_int(n) -> str:
    try:
        return f"{int(n):,}".replace(",", "\u202f")
    except Exception:
        return str(n) if n is not None else "—"


def fmt_pct(n, digits=1) -> str:
    try:
        return f"{float(n):.{digits}f}%"
    except Exception:
        return "—"


def fmt_float(n, digits=2) -> str:
    try:
        return f"{float(n):.{digits}f}"
    except Exception:
        return "—"


def progress_pct(current, target) -> float | None:
    """Returns 0-100 percent of target achieved. None if not computable."""
    try:
        c = float(current)
        t = float(target)
        if t == 0:
            return None
        return max(0.0, min(100.0, 100.0 * c / t))
    except Exception:
        return None


# ---------- Sections ----------
def section_north_star(data) -> str:
    ga4 = data.get("ga4", {})
    targets = data.get("targets", {})
    ns = targets.get("north_star", {})
    target = ns.get("target", 500)
    target_date = ns.get("target_date", "2026-08-31")

    latest = ga4.get("latest") or {}
    dau = latest.get("active")
    dau_date = latest.get("date", "—")
    avg7 = ga4.get("avg_dau_7d")
    avg28 = ga4.get("avg_dau_28d")

    pct = progress_pct(dau, target)
    pct_str = f"{pct:.0f}%" if pct is not None else "—"
    bar_w = f"{pct:.1f}%" if pct is not None else "0%"

    gap = ""
    try:
        if dau is not None:
            d = int(target) - int(dau)
            if d > 0:
                gap = f"<span class='ns-gap'>{fmt_int(d)} to goal</span>"
            else:
                gap = "<span class='ns-gap ok'>Goal reached</span>"
    except Exception:
        pass

    return f"""
<section class='north-star'>
  <div class='ns-head'>
    <div class='ns-label'>North Star</div>
    <div class='ns-target'>{fmt_int(target)} DAU by {esc(target_date)}</div>
  </div>
  <div class='ns-row'>
    <div class='ns-current'>
      <div class='ns-value'>{fmt_int(dau)}</div>
      <div class='ns-sub'>DAU on {esc(dau_date)}</div>
    </div>
    <div class='ns-progress-wrap'>
      <div class='ns-bar'>
        <div class='ns-bar-fill' style='width:{bar_w}'></div>
        <div class='ns-bar-target' title='Target {fmt_int(target)}'></div>
      </div>
      <div class='ns-progress-meta'>
        <span>{pct_str} of target</span>
        {gap}
      </div>
    </div>
    <div class='ns-aux'>
      <div><span class='lbl'>7d avg</span> <span class='val'>{fmt_int(avg7)}</span></div>
      <div><span class='lbl'>28d avg</span> <span class='val'>{fmt_int(avg28)}</span></div>
    </div>
  </div>
</section>"""


def _kpi_card(label, current_raw, target, fmt) -> str:
    if fmt == "int":
        cur_str = fmt_int(current_raw)
        tgt_str = fmt_int(target)
    elif fmt == "pct":
        cur_str = fmt_pct(current_raw, 1) if current_raw is not None else "—"
        tgt_str = fmt_pct(target, 0)
    elif fmt == "pct_lower":
        # lower is better (churn)
        cur_str = fmt_pct(current_raw, 1) if current_raw is not None else "—"
        tgt_str = "≤" + fmt_pct(target, 0)
    elif fmt == "float":
        cur_str = fmt_float(current_raw, 2) if current_raw is not None else "—"
        tgt_str = fmt_float(target, 1)
    else:
        cur_str = str(current_raw) if current_raw is not None else "—"
        tgt_str = str(target)

    pct = progress_pct(current_raw, target) if fmt != "pct_lower" else None
    if fmt == "pct_lower" and current_raw is not None and target:
        # invert: if current <= target -> 100%, else scale down
        try:
            c = float(current_raw)
            t = float(target)
            pct = 100.0 if c <= t else max(0.0, 100.0 - (c - t) * 5)
        except Exception:
            pct = None

    bar_w = f"{pct:.1f}%" if pct is not None else "0%"
    pct_label = f"{pct:.0f}% of goal" if pct is not None else ""

    return f"""
  <div class='kpi'>
    <div class='kpi-label'>{esc(label)}</div>
    <div class='kpi-value'>{cur_str}</div>
    <div class='kpi-target'>target {tgt_str}</div>
    <div class='kpi-bar'><div class='kpi-bar-fill' style='width:{bar_w}'></div></div>
    <div class='kpi-pct'>{pct_label}</div>
  </div>"""


def section_kpis(data) -> str:
    ga4 = data.get("ga4", {})
    kit = data.get("kit", {})
    asc = data.get("asc", {})
    bluesky = data.get("bluesky", {})
    mastodon = data.get("mastodon", {})
    targets = data.get("targets", {})

    latest = ga4.get("latest") or {}

    # Plus subscribers = currently active subscribers across iOS + Android
    play = data.get("play", {}) or {}
    ios_subs = (asc.get("subscriptions") or {}) if isinstance(asc, dict) else {}
    ios_active = ios_subs.get("active_subscribers") if ios_subs.get("status") == "ok" else None
    # Play: we don't have an active-count report yet, fall back to estimated active = new - cancellations in 30d
    play_new = play.get("new_subscribers_30d") if play.get("status") == "ok" else None
    play_events = (play.get("by_event_type") or {}) if play.get("status") == "ok" else {}
    play_cancels = sum(v for k, v in play_events.items() if "cancel" in k.lower())
    play_active = None
    if play_new is not None:
        play_active = max(0, (play_new or 0) - (play_cancels or 0))
    plus_total = None
    if ios_active is not None or play_active is not None:
        plus_total = (ios_active or 0) + (play_active or 0)

    values = {
        "dau_latest": latest.get("active"),
        "active_28d": ga4.get("total_active_28d"),
        "kit_subscribers": kit.get("active_subscribers"),
        "plus_subscribers": plus_total,
        "monthly_churn": None,
        "push_opt_in": None,
        "push_open_rate": None,
        "new_installs_30d": None,
        "avg_rating": asc.get("avg_rating_recent"),
        "reviews_4plus": _count_4plus(asc),
        "bluesky_followers": bluesky.get("followers"),
        "mastodon_followers": mastodon.get("followers"),
    }

    cards = []
    for s in targets.get("supporting", []):
        key = s["key"]
        cards.append(_kpi_card(s["label"], values.get(key), s["target"], s.get("format", "int")))

    return f"""
<section class='kpis'>
  <h2>Supporting KPIs</h2>
  <div class='kpi-grid'>
    {''.join(cards)}
  </div>
</section>"""


def _count_4plus(asc) -> int | None:
    if asc.get("status") != "ok":
        return None
    dist = asc.get("rating_distribution_recent", {})
    try:
        return int(dist.get(4, 0)) + int(dist.get(5, 0))
    except Exception:
        return None


def section_dau_chart(data) -> str:
    ga4 = data.get("ga4", {})
    rows = ga4.get("daily_users", [])
    if not rows:
        return "<section class='chart-section'><h2>DAU — last 90 days</h2><div class='empty'>No GA4 data available.</div></section>"

    target = data.get("targets", {}).get("north_star", {}).get("target", 500)
    target_date = data.get("targets", {}).get("north_star", {}).get("target_date", "2026-08-31")

    # SVG dims
    W, H = 920, 280
    PAD_L, PAD_R, PAD_T, PAD_B = 50, 16, 16, 30
    inner_w = W - PAD_L - PAD_R
    inner_h = H - PAD_T - PAD_B

    n = len(rows)
    vals = [r["active"] for r in rows]
    y_max = max(max(vals) * 1.1, target * 1.1, 50)

    def x_at(i):
        return PAD_L + (i / max(n - 1, 1)) * inner_w

    def y_at(v):
        return PAD_T + inner_h - (v / y_max) * inner_h

    # Polyline points
    pts = " ".join(f"{x_at(i):.1f},{y_at(v):.1f}" for i, v in enumerate(vals))

    # Area under line
    area_pts = (
        f"{PAD_L:.1f},{(PAD_T + inner_h):.1f} "
        + pts
        + f" {x_at(n - 1):.1f},{(PAD_T + inner_h):.1f}"
    )

    # Target line
    target_y = y_at(target)
    target_line = (
        f"<line x1='{PAD_L}' y1='{target_y:.1f}' x2='{W - PAD_R}' y2='{target_y:.1f}' "
        f"stroke='#f5b942' stroke-width='1.5' stroke-dasharray='5,4' />"
    )
    target_text = (
        f"<text x='{W - PAD_R - 4}' y='{target_y - 6:.1f}' fill='#f5b942' "
        f"font-size='11' text-anchor='end'>Target {fmt_int(target)} by {esc(target_date)}</text>"
    )

    # Y-axis ticks
    y_ticks = []
    for frac in [0, 0.25, 0.5, 0.75, 1.0]:
        v = y_max * frac
        y = y_at(v)
        y_ticks.append(
            f"<line x1='{PAD_L}' y1='{y:.1f}' x2='{W - PAD_R}' y2='{y:.1f}' stroke='#1f2735' stroke-width='1'/>"
            f"<text x='{PAD_L - 6}' y='{y + 3:.1f}' fill='#8a99b3' font-size='10' text-anchor='end'>{fmt_int(int(v))}</text>"
        )

    # X-axis tick labels (first, mid, last)
    x_ticks = []
    for i in [0, n // 2, n - 1]:
        if 0 <= i < n:
            x = x_at(i)
            label = rows[i]["date"][5:]  # MM-DD
            x_ticks.append(
                f"<text x='{x:.1f}' y='{H - 8}' fill='#8a99b3' font-size='10' text-anchor='middle'>{label}</text>"
            )

    latest_val = rows[-1]["active"]
    latest_x = x_at(n - 1)
    latest_y = y_at(latest_val)
    latest_dot = (
        f"<circle cx='{latest_x:.1f}' cy='{latest_y:.1f}' r='4' fill='#5fb3ff' stroke='#0b1220' stroke-width='2'/>"
    )

    return f"""
<section class='chart-section'>
  <h2>DAU — last 90 days</h2>
  <svg viewBox='0 0 {W} {H}' xmlns='http://www.w3.org/2000/svg' role='img' aria-label='Daily active users chart'>
    {''.join(y_ticks)}
    <polygon points='{area_pts}' fill='rgba(95,179,255,0.12)' />
    <polyline points='{pts}' fill='none' stroke='#5fb3ff' stroke-width='2'/>
    {target_line}
    {target_text}
    {latest_dot}
    {''.join(x_ticks)}
  </svg>
</section>"""


def section_newsletter(data) -> str:
    kit = data.get("kit", {})
    if kit.get("status") == "skipped":
        return f"<section><h2>Newsletter (Kit)</h2><div class='empty'>Skipped — {esc(kit.get('reason'))}</div></section>"
    if kit.get("status") == "error":
        return f"<section><h2>Newsletter (Kit)</h2><div class='empty err'>Error: {esc(kit.get('error'))}</div></section>"

    active = kit.get("active_subscribers", 0)
    inactive = kit.get("inactive_subscribers", 0)
    broadcasts = kit.get("recent_broadcasts", [])

    rows = []
    for b in broadcasts[:10]:
        sent = b.get("send_at") or "—"
        if sent and sent != "—":
            sent = sent[:10]
        rows.append(
            f"<tr><td>{esc(sent)}</td><td>{esc(b.get('subject', ''))}</td>"
            f"<td>{'public' if b.get('public') else 'subs only'}</td></tr>"
        )
    table = (
        f"<table class='tbl'><thead><tr><th>Date</th><th>Subject</th><th>Audience</th></tr></thead>"
        f"<tbody>{''.join(rows) or '<tr><td colspan=3 class=empty>No broadcasts yet</td></tr>'}</tbody></table>"
    )

    return f"""
<section>
  <h2>Newsletter</h2>
  <div class='kit-stats'>
    <div><span class='lbl'>Active</span> <span class='val'>{fmt_int(active)}</span></div>
    <div><span class='lbl'>Inactive</span> <span class='val'>{fmt_int(inactive)}</span></div>
  </div>
  {table}
</section>"""


def section_socials(data) -> str:
    bs = data.get("bluesky", {})
    md = data.get("mastodon", {})
    th = data.get("threads", {})
    ig = data.get("instagram", {})

    def card(name, src):
        st = src.get("status")
        if st == "ok":
            return f"""
  <div class='social-card'>
    <div class='social-name'>{esc(name)}</div>
    <div class='social-handle'>{esc(src.get('handle') or src.get('username') or '')}</div>
    <div class='social-stats'>
      <div><span class='lbl'>Followers</span> <span class='val'>{fmt_int(src.get('followers'))}</span></div>
      <div><span class='lbl'>Posts 7d</span> <span class='val'>{fmt_int(src.get('posts_7d'))}</span></div>
      <div><span class='lbl'>Engagement 7d</span> <span class='val'>{fmt_int((src.get('likes_7d') or src.get('favs_7d') or 0) + (src.get('reposts_7d') or src.get('boosts_7d') or 0) + (src.get('comments_7d') or 0))}</span></div>
    </div>
  </div>"""
        if st == "blocked":
            return f"""
  <div class='social-card blocked'>
    <div class='social-name'>{esc(name)}</div>
    <div class='social-blocked'>Blocked</div>
    <div class='social-reason'>{esc(src.get('reason', ''))}</div>
  </div>"""
        if st == "error":
            return f"""
  <div class='social-card err'>
    <div class='social-name'>{esc(name)}</div>
    <div class='social-blocked'>Error</div>
    <div class='social-reason'>{esc(src.get('error', ''))}</div>
  </div>"""
        return f"""
  <div class='social-card skipped'>
    <div class='social-name'>{esc(name)}</div>
    <div class='social-blocked'>Skipped</div>
    <div class='social-reason'>{esc(src.get('reason', ''))}</div>
  </div>"""

    return f"""
<section>
  <h2>Social channels</h2>
  <div class='social-grid'>
    {card('Bluesky', bs)}
    {card('Mastodon', md)}
    {card('Threads', th)}
    {card('Instagram', ig)}
  </div>
</section>"""


def section_app_store(data) -> str:
    asc = data.get("asc", {})
    if asc.get("status") != "ok":
        reason = asc.get("reason") or asc.get("error") or "no data"
        return f"<section><h2>App Store reviews</h2><div class='empty'>Not available — {esc(reason)}</div></section>"

    reviews = asc.get("reviews_recent", [])
    stats_30d = asc.get("stats_30d", {})
    stats_90d = asc.get("stats_90d", {})
    stats_all = asc.get("stats_all_time", {})
    monthly = asc.get("monthly", [])
    new_run = asc.get("new_this_run", 0)

    def _card(label, s):
        avg = s.get("avg")
        cnt = s.get("count", 0)
        share = s.get("share_4plus")
        return f"""
  <div class='asc-stat-card'>
    <div class='asc-stat-label'>{esc(label)}</div>
    <div class='asc-stat-row'>
      <div class='asc-stat-main'>
        <div class='asc-stat-val'>{fmt_float(avg, 2) if avg is not None else '—'}</div>
        <div class='asc-stat-sub'>avg · {fmt_int(cnt)} reviews</div>
      </div>
      <div class='asc-stat-side'>
        <div class='asc-stat-share'>{fmt_pct(share, 0) if share is not None else '—'}</div>
        <div class='asc-stat-sub'>4★ or 5★</div>
      </div>
    </div>
  </div>"""

    stat_cards = (
        _card("Last 30 days", stats_30d)
        + _card("Last 90 days", stats_90d)
        + _card("All-time tracked", stats_all)
    )

    chart_html = ""
    if monthly:
        W, H = 920, 200
        PAD_L, PAD_R, PAD_T, PAD_B = 50, 16, 16, 30
        inner_w = W - PAD_L - PAD_R
        inner_h = H - PAD_T - PAD_B
        n = len(monthly)

        def x_at(i):
            return PAD_L + (i / max(n - 1, 1)) * inner_w

        def y_avg(v):
            return PAD_T + inner_h - ((v - 1) / 4) * inner_h

        def y_share(v):
            return PAD_T + inner_h - (v / 100) * inner_h

        avg_pts = " ".join(f"{x_at(i):.1f},{y_avg(m['avg']):.1f}" for i, m in enumerate(monthly))
        share_pts = " ".join(f"{x_at(i):.1f},{y_share(m['share_4plus']):.1f}" for i, m in enumerate(monthly))

        y_ticks = []
        for v in [1, 2, 3, 4, 5]:
            y = y_avg(v)
            y_ticks.append(
                f"<line x1='{PAD_L}' y1='{y:.1f}' x2='{W - PAD_R}' y2='{y:.1f}' stroke='#1f2735' stroke-width='1'/>"
                f"<text x='{PAD_L - 6}' y='{y + 3:.1f}' fill='#8a99b3' font-size='10' text-anchor='end'>{v}★</text>"
            )

        x_labels = []
        for i, m in enumerate(monthly):
            if n <= 6 or i % max(1, n // 6) == 0 or i == n - 1:
                x = x_at(i)
                x_labels.append(
                    f"<text x='{x:.1f}' y='{H - 8}' fill='#8a99b3' font-size='10' text-anchor='middle'>{esc(m['month'][2:])}</text>"
                )

        avg_dots = "".join(
            f"<circle cx='{x_at(i):.1f}' cy='{y_avg(m['avg']):.1f}' r='3' fill='#5fb3ff'>"
            f"<title>{esc(m['month'])} — avg {m['avg']} · {m['count']} reviews</title></circle>"
            for i, m in enumerate(monthly)
        )
        share_dots = "".join(
            f"<circle cx='{x_at(i):.1f}' cy='{y_share(m['share_4plus']):.1f}' r='3' fill='#4ade80'>"
            f"<title>{esc(m['month'])} — {m['share_4plus']}% 4★+</title></circle>"
            for i, m in enumerate(monthly)
        )

        chart_html = f"""
  <div class='asc-trend'>
    <div class='asc-trend-head'>
      <span class='asc-legend'><span class='legend-dot' style='background:#5fb3ff'></span>Average rating</span>
      <span class='asc-legend'><span class='legend-dot' style='background:#4ade80'></span>Share 4★+</span>
    </div>
    <svg viewBox='0 0 {W} {H}' xmlns='http://www.w3.org/2000/svg' role='img'>
      {''.join(y_ticks)}
      <polyline points='{avg_pts}' fill='none' stroke='#5fb3ff' stroke-width='2'/>
      <polyline points='{share_pts}' fill='none' stroke='#4ade80' stroke-width='2' stroke-dasharray='4,4'/>
      {avg_dots}
      {share_dots}
      {''.join(x_labels)}
    </svg>
  </div>"""

    rev_html = []
    for r in reviews[:10]:
        rating = int(r.get("rating", 0))
        stars = "★" * rating + "☆" * (5 - rating)
        created = (r.get("created") or "")[:10]
        rev_html.append(
            f"<div class='review'>"
            f"<div class='review-head'><span class='review-stars'>{stars}</span>"
            f"<span class='review-meta'>{esc(r.get('reviewer'))} · {esc(r.get('territory'))} · {esc(created)}</span></div>"
            f"<div class='review-title'>{esc(r.get('title'))}</div>"
            f"<div class='review-body'>{esc(r.get('body'))}</div>"
            f"</div>"
        )

    new_badge = f"<span class='asc-new-badge'>+{new_run} new</span>" if new_run else ""

    return f"""
<section>
  <h2>App Store reviews {new_badge}</h2>
  <div class='asc-stat-grid'>
    {stat_cards}
  </div>
  {chart_html}
  <h3 class='asc-recent-h'>10 most recent</h3>
  <div class='reviews'>{''.join(rev_html) or '<div class=empty>No reviews returned.</div>'}</div>
</section>"""


def section_subscriptions_play(data) -> str:
    play = data.get("play", {}) or {}
    if play.get("status") != "ok":
        reason = play.get("reason") or play.get("error") or "no data"
        return f"<section><h2>Subscriptions — Android</h2><div class='empty'>Not available — {esc(reason)}</div></section>"

    window_start = play.get("window_start", "")
    window_end = play.get("window_end", "")
    total_units = play.get("total_units_30d", 0) or 0
    total_proceeds = play.get("total_proceeds_usd_30d", 0.0) or 0.0
    new_subs = play.get("new_subscribers_30d", 0) or 0
    by_product = play.get("by_product", {}) or {}
    by_day = play.get("by_day", []) or []
    by_country = play.get("by_country", []) or []
    by_event_type = play.get("by_event_type", {}) or {}

    monthly_units = 0
    yearly_units = 0
    monthly_proceeds = 0.0
    yearly_proceeds = 0.0
    for sku, info in by_product.items():
        units = info.get("units", 0) or 0
        proceeds = info.get("proceeds_usd", 0.0) or 0.0
        if sku.endswith(".monthly") or "monthly" in sku.lower():
            monthly_units += units
            monthly_proceeds += proceeds
        elif sku.endswith(".yearly") or "yearly" in sku.lower():
            yearly_units += units
            yearly_proceeds += proceeds

    def _kpi(label, value, sub):
        return f"""
  <div class='asc-stat-card'>
    <div class='asc-stat-label'>{esc(label)}</div>
    <div class='asc-stat-row'>
      <div class='asc-stat-main'>
        <div class='asc-stat-val'>{value}</div>
        <div class='asc-stat-sub'>{esc(sub)}</div>
      </div>
    </div>
  </div>"""

    kpi_cards = (
        _kpi("Units (30d)", fmt_int(total_units), "billing events")
        + _kpi("Proceeds (30d)", f"${fmt_float(total_proceeds, 2)}", "merchant currency, after Google's cut")
        + _kpi("New subscribers (30d)", fmt_int(new_subs), "first-time conversions")
        + _kpi("Monthly / Yearly", f"{fmt_int(monthly_units)} / {fmt_int(yearly_units)}", f"${fmt_float(monthly_proceeds, 2)} / ${fmt_float(yearly_proceeds, 2)}")
    )

    chart_html = ""
    if by_day:
        W, H = 920, 180
        PAD_L, PAD_R, PAD_T, PAD_B = 40, 16, 16, 28
        inner_w = W - PAD_L - PAD_R
        inner_h = H - PAD_T - PAD_B
        n = len(by_day)
        max_units = max((d.get("monthly", 0) + d.get("yearly", 0) + d.get("other", 0)) for d in by_day) or 1
        if max_units < 5:
            y_max = 5
        elif max_units < 10:
            y_max = 10
        else:
            y_max = ((max_units // 5) + 1) * 5

        bar_w = inner_w / n * 0.7
        gap = inner_w / n

        def y_at(v):
            return PAD_T + inner_h - (v / y_max) * inner_h

        y_ticks = []
        for v in [0, y_max // 2, y_max]:
            y = y_at(v)
            y_ticks.append(
                f"<line x1='{PAD_L}' y1='{y:.1f}' x2='{W - PAD_R}' y2='{y:.1f}' stroke='#1f2735' stroke-width='1'/>"
                f"<text x='{PAD_L - 6}' y='{y + 3:.1f}' fill='#8a99b3' font-size='10' text-anchor='end'>{v}</text>"
            )

        bars = []
        x_labels = []
        for i, d in enumerate(by_day):
            m_u = d.get("monthly", 0) or 0
            y_u = d.get("yearly", 0) or 0
            o_u = d.get("other", 0) or 0
            x = PAD_L + i * gap + (gap - bar_w) / 2
            base_y = PAD_T + inner_h
            m_h = (m_u / y_max) * inner_h
            y_h = (y_u / y_max) * inner_h
            o_h = (o_u / y_max) * inner_h
            tooltip = f"{d.get('date', '')}: M {m_u}, Y {y_u}, other {o_u}"
            if m_u:
                bars.append(f"<rect x='{x:.1f}' y='{base_y - m_h:.1f}' width='{bar_w:.1f}' height='{m_h:.1f}' fill='#5fb3ff'><title>{esc(tooltip)}</title></rect>")
            if y_u:
                bars.append(f"<rect x='{x:.1f}' y='{base_y - m_h - y_h:.1f}' width='{bar_w:.1f}' height='{y_h:.1f}' fill='#4ade80'><title>{esc(tooltip)}</title></rect>")
            if o_u:
                bars.append(f"<rect x='{x:.1f}' y='{base_y - m_h - y_h - o_h:.1f}' width='{bar_w:.1f}' height='{o_h:.1f}' fill='#fbbf24'><title>{esc(tooltip)}</title></rect>")
            if n <= 10 or i % max(1, n // 8) == 0 or i == n - 1:
                date_lbl = (d.get("date") or "")[5:]
                x_labels.append(
                    f"<text x='{x + bar_w / 2:.1f}' y='{H - 8}' fill='#8a99b3' font-size='10' text-anchor='middle'>{esc(date_lbl)}</text>"
                )

        chart_html = f"""
  <div class='asc-trend'>
    <div class='asc-trend-head'>
      <span class='asc-legend'><span class='legend-dot' style='background:#5fb3ff'></span>Monthly</span>
      <span class='asc-legend'><span class='legend-dot' style='background:#4ade80'></span>Yearly</span>
      <span class='asc-legend'><span class='legend-dot' style='background:#fbbf24'></span>Other</span>
    </div>
    <svg viewBox='0 0 {W} {H}' xmlns='http://www.w3.org/2000/svg' role='img'>
      {''.join(y_ticks)}
      {''.join(bars)}
      {''.join(x_labels)}
    </svg>
  </div>"""

    ctry_html = ""
    if by_country:
        top = by_country[:10]
        max_u = max((c.get("units", 0) for c in top), default=1) or 1
        rows = []
        for c in top:
            country = c.get("country", "??")
            units = c.get("units", 0) or 0
            proceeds = c.get("proceeds_usd", 0.0) or 0.0
            pct = (units / max_u) * 100
            rows.append(
                f"<div class='ctry-row'>"
                f"<div>{esc(country)}</div>"
                f"<div class='ctry-bar'><div class='ctry-fill' style='width:{pct:.0f}%'></div></div>"
                f"<div class='ctry-val'>{fmt_int(units)} · ${fmt_float(proceeds, 2)}</div>"
                f"</div>"
            )
        ctry_html = f"<h3 class='asc-recent-h'>Top countries</h3>{''.join(rows)}"

    et_html = ""
    if by_event_type:
        items = sorted(by_event_type.items(), key=lambda kv: kv[1], reverse=True)
        chips = "".join(
            f"<span class='chip'>{esc(name)} · {fmt_int(count)}</span>"
            for name, count in items
        )
        et_html = f"<h3 class='asc-recent-h'>Event types</h3><div class='chips'>{chips}</div>"

    prod_html = ""
    if by_product:
        items = sorted(by_product.items(), key=lambda kv: kv[1].get("units", 0) or 0, reverse=True)
        rows = []
        for sku, info in items:
            name = info.get("name") or sku
            units = info.get("units", 0) or 0
            proceeds = info.get("proceeds_usd", 0.0) or 0.0
            rows.append(
                f"<div class='ctry-row'>"
                f"<div>{esc(name)}</div>"
                f"<div style='color:var(--muted);font-size:11px'>{esc(sku)}</div>"
                f"<div class='ctry-val'>{fmt_int(units)} · ${fmt_float(proceeds, 2)}</div>"
                f"</div>"
            )
        prod_html = f"<h3 class='asc-recent-h'>By product</h3>{''.join(rows)}"

    window_lbl = f"{window_start} → {window_end}" if window_start else ""

    return f"""
<section>
  <h2>Subscriptions — Android <span class='asc-stat-sub' style='font-weight:normal'>{esc(window_lbl)}</span></h2>
  <div class='asc-stat-grid'>
    {kpi_cards}
  </div>
  {chart_html}
  {prod_html}
  {ctry_html}
  {et_html}
</section>"""


def section_subscriptions(data) -> str:
    asc = data.get("asc", {}) or {}
    subs = asc.get("subscriptions", {}) or {}
    if subs.get("status") != "ok":
        reason = subs.get("reason") or subs.get("error") or "no data"
        return f"<section><h2>Subscriptions — iOS</h2><div class='empty'>Not available — {esc(reason)}</div></section>"

    window_start = subs.get("window_start", "")
    window_end = subs.get("window_end", "")
    days_with_data = subs.get("days_with_data", 0)
    days_attempted = subs.get("days_attempted", 0)
    total_units = subs.get("total_units_30d", 0) or 0
    total_proceeds = subs.get("total_proceeds_usd_30d", 0.0) or 0.0
    new_subs = subs.get("new_subscribers_30d", 0) or 0
    by_product = subs.get("by_product", {}) or {}
    by_day = subs.get("by_day", []) or []
    by_country = subs.get("by_country", []) or []
    by_order_type = subs.get("by_order_type", {}) or {}

    monthly_units = 0
    yearly_units = 0
    monthly_proceeds = 0.0
    yearly_proceeds = 0.0
    for sku, info in by_product.items():
        units = info.get("units", 0) or 0
        proceeds = info.get("proceeds_usd", 0.0) or 0.0
        if sku.endswith(".monthly"):
            monthly_units += units
            monthly_proceeds += proceeds
        elif sku.endswith(".yearly"):
            yearly_units += units
            yearly_proceeds += proceeds

    def _kpi(label, value, sub):
        return f"""
  <div class='asc-stat-card'>
    <div class='asc-stat-label'>{esc(label)}</div>
    <div class='asc-stat-row'>
      <div class='asc-stat-main'>
        <div class='asc-stat-val'>{value}</div>
        <div class='asc-stat-sub'>{esc(sub)}</div>
      </div>
    </div>
  </div>"""

    active_breakdown = subs.get("active_breakdown", {}) or {}
    active_total = active_breakdown.get("active_total")
    arr_usd = active_breakdown.get("arr_usd")
    mrr_usd = active_breakdown.get("mrr_usd")
    proceeds_factor = active_breakdown.get("proceeds_factor", 0.85)
    arr_sub = f"MRR ~${fmt_float(mrr_usd or 0, 2)} · after Apple {int(round((1 - proceeds_factor) * 100))}% cut" if arr_usd is not None else "no data"
    arr_val = f"${fmt_float(arr_usd or 0, 2)}" if arr_usd is not None else "—"
    active_sub = "currently paying + free trial" if active_total is not None else ""
    active_val = fmt_int(active_total) if active_total is not None else "—"

    kpi_cards = (
        _kpi("Active subscribers", active_val, active_sub)
        + _kpi("Estimated ARR", arr_val, arr_sub)
        + _kpi("Units (30d)", fmt_int(total_units), f"{days_with_data}/{days_attempted} days with data")
        + _kpi("Proceeds (30d)", f"${fmt_float(total_proceeds, 2)}", "USD, after Apple's cut")
        + _kpi("New subscribers (30d)", fmt_int(new_subs), "first-time conversions")
        + _kpi("Monthly / Yearly", f"{fmt_int(monthly_units)} / {fmt_int(yearly_units)}", f"${fmt_float(monthly_proceeds, 2)} / ${fmt_float(yearly_proceeds, 2)}")
    )

    chart_html = ""
    if by_day:
        W, H = 920, 180
        PAD_L, PAD_R, PAD_T, PAD_B = 40, 16, 16, 28
        inner_w = W - PAD_L - PAD_R
        inner_h = H - PAD_T - PAD_B
        n = len(by_day)
        max_units = max((d.get("monthly", 0) + d.get("yearly", 0) + d.get("other", 0)) for d in by_day) or 1
        if max_units < 5:
            y_max = 5
        elif max_units < 10:
            y_max = 10
        else:
            y_max = ((max_units // 5) + 1) * 5

        bar_w = inner_w / n * 0.7
        gap = inner_w / n

        def y_at(v):
            return PAD_T + inner_h - (v / y_max) * inner_h

        y_ticks = []
        for v in [0, y_max // 2, y_max]:
            y = y_at(v)
            y_ticks.append(
                f"<line x1='{PAD_L}' y1='{y:.1f}' x2='{W - PAD_R}' y2='{y:.1f}' stroke='#1f2735' stroke-width='1'/>"
                f"<text x='{PAD_L - 6}' y='{y + 3:.1f}' fill='#8a99b3' font-size='10' text-anchor='end'>{v}</text>"
            )

        bars = []
        x_labels = []
        for i, d in enumerate(by_day):
            m_u = d.get("monthly", 0) or 0
            y_u = d.get("yearly", 0) or 0
            o_u = d.get("other", 0) or 0
            x = PAD_L + i * gap + (gap - bar_w) / 2
            base_y = PAD_T + inner_h
            m_h = (m_u / y_max) * inner_h
            y_h = (y_u / y_max) * inner_h
            o_h = (o_u / y_max) * inner_h
            tooltip = f"{d.get('date', '')}: M {m_u}, Y {y_u}, other {o_u}"
            if m_u:
                bars.append(f"<rect x='{x:.1f}' y='{base_y - m_h:.1f}' width='{bar_w:.1f}' height='{m_h:.1f}' fill='#5fb3ff'><title>{esc(tooltip)}</title></rect>")
            if y_u:
                bars.append(f"<rect x='{x:.1f}' y='{base_y - m_h - y_h:.1f}' width='{bar_w:.1f}' height='{y_h:.1f}' fill='#4ade80'><title>{esc(tooltip)}</title></rect>")
            if o_u:
                bars.append(f"<rect x='{x:.1f}' y='{base_y - m_h - y_h - o_h:.1f}' width='{bar_w:.1f}' height='{o_h:.1f}' fill='#fbbf24'><title>{esc(tooltip)}</title></rect>")
            if n <= 10 or i % max(1, n // 8) == 0 or i == n - 1:
                date_lbl = (d.get("date") or "")[5:]
                x_labels.append(
                    f"<text x='{x + bar_w / 2:.1f}' y='{H - 8}' fill='#8a99b3' font-size='10' text-anchor='middle'>{esc(date_lbl)}</text>"
                )

        chart_html = f"""
  <div class='asc-trend'>
    <div class='asc-trend-head'>
      <span class='asc-legend'><span class='legend-dot' style='background:#5fb3ff'></span>Monthly</span>
      <span class='asc-legend'><span class='legend-dot' style='background:#4ade80'></span>Yearly</span>
      <span class='asc-legend'><span class='legend-dot' style='background:#fbbf24'></span>Other</span>
    </div>
    <svg viewBox='0 0 {W} {H}' xmlns='http://www.w3.org/2000/svg' role='img'>
      {''.join(y_ticks)}
      {''.join(bars)}
      {''.join(x_labels)}
    </svg>
  </div>"""

    ctry_html = ""
    if by_country:
        top = by_country[:10]
        max_u = max((c.get("units", 0) for c in top), default=1) or 1
        rows = []
        for c in top:
            country = c.get("country", "??")
            units = c.get("units", 0) or 0
            proceeds = c.get("proceeds_usd", 0.0) or 0.0
            pct = (units / max_u) * 100
            rows.append(
                f"<div class='ctry-row'>"
                f"<div>{esc(country)}</div>"
                f"<div class='ctry-bar'><div class='ctry-fill' style='width:{pct:.0f}%'></div></div>"
                f"<div class='ctry-val'>{fmt_int(units)} · ${fmt_float(proceeds, 2)}</div>"
                f"</div>"
            )
        ctry_html = f"<h3 class='asc-recent-h'>Top countries</h3>{''.join(rows)}"

    ot_html = ""
    if by_order_type:
        items = sorted(by_order_type.items(), key=lambda kv: kv[1], reverse=True)
        chips = "".join(
            f"<span class='chip'>{esc(name)} · {fmt_int(count)}</span>"
            for name, count in items
        )
        ot_html = f"<h3 class='asc-recent-h'>Order types</h3><div class='chips'>{chips}</div>"

    prod_html = ""
    if by_product:
        items = sorted(by_product.items(), key=lambda kv: kv[1].get("units", 0) or 0, reverse=True)
        rows = []
        for sku, info in items:
            name = info.get("name") or sku
            units = info.get("units", 0) or 0
            proceeds = info.get("proceeds_usd", 0.0) or 0.0
            rows.append(
                f"<div class='ctry-row'>"
                f"<div>{esc(name)}</div>"
                f"<div style='color:var(--muted);font-size:11px'>{esc(sku)}</div>"
                f"<div class='ctry-val'>{fmt_int(units)} · ${fmt_float(proceeds, 2)}</div>"
                f"</div>"
            )
        prod_html = f"<h3 class='asc-recent-h'>By product</h3>{''.join(rows)}"

    window_lbl = f"{window_start} → {window_end}" if window_start else ""

    return f"""
<section>
  <h2>Subscriptions — iOS <span class='asc-stat-sub' style='font-weight:normal'>{esc(window_lbl)}</span></h2>
  <div class='asc-stat-grid'>
    {kpi_cards}
  </div>
  {chart_html}
  {prod_html}
  {ctry_html}
  {ot_html}
</section>"""


def section_roadmap(data) -> str:
    rm = data.get("roadmap", {})
    if rm.get("status") != "ok":
        return f"<section><h2>Roadmap</h2><div class='empty'>{esc(rm.get('reason', 'No roadmap data'))}</div></section>"

    def col(name, label, items):
        rows = [
            f"<li><span class='rm-title'>{esc(it['title'])}</span>"
            + (f"<span class='rm-note'>{esc(it['note'])}</span>" if it.get('note') else "")
            + "</li>"
            for it in items
        ]
        return f"""
  <div class='rm-col rm-{name}'>
    <h3>{esc(label)} <span class='rm-count'>{len(items)}</span></h3>
    <ul>{''.join(rows) or '<li class=empty>None</li>'}</ul>
  </div>"""

    return f"""
<section>
  <h2>Roadmap</h2>
  <div class='roadmap-grid'>
    {col('in_progress', 'In progress', rm.get('in_progress', []))}
    {col('upcoming', 'Upcoming', rm.get('upcoming', []))}
    {col('blocked', 'Blocked', rm.get('blocked', []))}
    {col('completed', 'Completed', rm.get('completed', []))}
  </div>
</section>"""


def section_countries(data) -> str:
    ga4 = data.get("ga4", {})
    countries = ga4.get("top_countries_30d", [])
    if not countries:
        return ""
    total = sum(c["active"] for c in countries) or 1
    rows = []
    for c in countries:
        pct = c["active"] / total * 100
        rows.append(
            f"<div class='ctry-row'>"
            f"<span class='ctry-name'>{esc(c['country'] or '—')}</span>"
            f"<div class='ctry-bar'><div class='ctry-fill' style='width:{pct:.1f}%'></div></div>"
            f"<span class='ctry-val'>{fmt_int(c['active'])}</span>"
            f"</div>"
        )
    return f"""
<section>
  <h2>Top countries (30d active users)</h2>
  <div class='ctry-list'>{''.join(rows)}</div>
</section>"""


def section_push(data) -> str:
    push = data.get("push", {})
    if push.get("status") != "ok":
        return ""
    rows = push.get("recent", [])
    if not rows:
        return ""
    tr_html = []
    for r in rows[:10]:
        tr_html.append(
            f"<tr><td>{esc((r.get('sent_at') or '')[:16])}</td>"
            f"<td>{esc(r.get('title', ''))}</td>"
            f"<td>{esc(r.get('platform', ''))}</td>"
            f"<td>{esc(r.get('sent_count', ''))}</td></tr>"
        )
    return f"""
<section>
  <h2>Recent push campaigns</h2>
  <table class='tbl'>
    <thead><tr><th>Sent</th><th>Title</th><th>Platform</th><th>Sent</th></tr></thead>
    <tbody>{''.join(tr_html)}</tbody>
  </table>
</section>"""


def section_health(data) -> str:
    sources = [
        ("GA4", data.get("ga4", {})),
        ("Kit", data.get("kit", {})),
        ("App Store Connect", data.get("asc", {})),
        ("Bluesky", data.get("bluesky", {})),
        ("Mastodon", data.get("mastodon", {})),
        ("Threads", data.get("threads", {})),
        ("Instagram", data.get("instagram", {})),
        ("Push history", data.get("push", {})),
        ("Roadmap", data.get("roadmap", {})),
    ]
    chips = []
    for name, src in sources:
        st = src.get("status", "unknown")
        chips.append(
            f"<span class='chip chip-{esc(st)}' title='{esc(src.get('reason') or src.get('error') or src.get('fetched_at') or '')}'>"
            f"{esc(name)} · {esc(st)}</span>"
        )
    return f"""
<section class='health'>
  <h2>Source status</h2>
  <div class='chips'>{''.join(chips)}</div>
</section>"""


# ---------- Page template ----------
CSS = """
:root {
  --bg: #0b1220;
  --bg-card: #121a2c;
  --bg-card-2: #182241;
  --line: #1f2735;
  --text: #e6ecf5;
  --muted: #8a99b3;
  --accent: #5fb3ff;
  --accent-2: #f5b942;
  --ok: #4ade80;
  --warn: #fbbf24;
  --err: #f87171;
  --skipped: #6b7280;
}
* { box-sizing: border-box; }
html, body { background: var(--bg); color: var(--text); margin: 0; padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  font-size: 14px; line-height: 1.5; }
a { color: var(--accent); text-decoration: none; }
main { max-width: 1100px; margin: 0 auto; padding: 24px 20px 80px; }
header.page { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 24px; }
header.page h1 { font-size: 22px; margin: 0; letter-spacing: 0.2px; }
header.page .gen { color: var(--muted); font-size: 12px; }
h2 { font-size: 16px; letter-spacing: 0.3px; margin: 0 0 12px; color: var(--text); }
section { background: var(--bg-card); border: 1px solid var(--line); border-radius: 10px;
  padding: 18px; margin-bottom: 18px; }
.empty { color: var(--muted); font-style: normal; padding: 6px 0; }
.empty.err { color: var(--err); }

/* North Star */
.north-star { background: linear-gradient(135deg, #182241 0%, #121a2c 100%); }
.ns-head { display:flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px; }
.ns-label { color: var(--muted); text-transform: uppercase; letter-spacing: 1.2px; font-size: 11px; }
.ns-target { color: var(--accent-2); font-size: 13px; }
.ns-row { display: grid; grid-template-columns: 180px 1fr 180px; gap: 24px; align-items: center; }
.ns-current .ns-value { font-size: 44px; font-weight: 600; line-height: 1; color: var(--text); }
.ns-current .ns-sub { color: var(--muted); font-size: 12px; margin-top: 6px; }
.ns-bar { position: relative; height: 14px; background: #0b1220; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
.ns-bar-fill { height: 100%; background: linear-gradient(90deg, #5fb3ff, #4ade80); }
.ns-progress-meta { display: flex; justify-content: space-between; color: var(--muted); font-size: 12px; margin-top: 6px; }
.ns-gap { color: var(--accent-2); }
.ns-gap.ok { color: var(--ok); }
.ns-aux { display: flex; flex-direction: column; gap: 6px; font-size: 13px; }
.ns-aux .lbl { color: var(--muted); margin-right: 8px; }
.ns-aux .val { color: var(--text); font-weight: 500; }

/* KPI grid */
.kpi-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
.kpi { background: var(--bg-card-2); border: 1px solid var(--line); border-radius: 8px; padding: 12px; }
.kpi-label { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; }
.kpi-value { font-size: 24px; font-weight: 600; margin-top: 4px; }
.kpi-target { color: var(--muted); font-size: 11px; margin-top: 2px; }
.kpi-bar { height: 4px; background: #0b1220; border-radius: 4px; margin-top: 8px; overflow: hidden; }
.kpi-bar-fill { height: 100%; background: var(--accent); }
.kpi-pct { color: var(--muted); font-size: 10px; margin-top: 4px; }

/* Chart */
.chart-section svg { width: 100%; height: auto; display: block; }

/* Tables */
.tbl { width: 100%; border-collapse: collapse; font-size: 13px; }
.tbl th, .tbl td { padding: 8px 10px; border-bottom: 1px solid var(--line); text-align: left; }
.tbl th { color: var(--muted); font-weight: 500; text-transform: uppercase; font-size: 10px; letter-spacing: 0.8px; }

.kit-stats { display: flex; gap: 24px; margin-bottom: 14px; }
.kit-stats .lbl { color: var(--muted); font-size: 11px; }
.kit-stats .val { font-size: 18px; margin-left: 6px; }

/* Socials */
.social-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
.social-card { background: var(--bg-card-2); border: 1px solid var(--line); border-radius: 8px; padding: 14px; }
.social-card.blocked, .social-card.skipped { opacity: 0.6; }
.social-card.err { border-color: rgba(248, 113, 113, 0.4); }
.social-name { font-weight: 600; }
.social-handle { color: var(--muted); font-size: 12px; margin-bottom: 8px; }
.social-blocked { color: var(--warn); font-size: 12px; }
.social-reason { color: var(--muted); font-size: 11px; margin-top: 4px; }
.social-stats { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 4px; margin-top: 8px; }
.social-stats .lbl { color: var(--muted); font-size: 10px; display: block; }
.social-stats .val { font-weight: 600; }

/* App Store */
.asc-stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-bottom: 16px; }
.asc-stat-card { background: var(--bg-card-2); border: 1px solid var(--line); border-radius: 8px; padding: 12px 14px; }
.asc-stat-label { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px; }
.asc-stat-row { display: flex; justify-content: space-between; align-items: flex-end; }
.asc-stat-val { font-size: 28px; font-weight: 600; line-height: 1; }
.asc-stat-share { font-size: 22px; font-weight: 600; color: var(--ok); line-height: 1; }
.asc-stat-sub { color: var(--muted); font-size: 11px; margin-top: 3px; }
.asc-stat-side { text-align: right; }
.asc-new-badge { background: var(--accent); color: #0b1220; border-radius: 10px; padding: 2px 10px; font-size: 11px; font-weight: 600; margin-left: 8px; vertical-align: middle; }
.asc-trend { margin: 12px 0 18px; }
.asc-trend-head { display: flex; gap: 16px; color: var(--muted); font-size: 11px; margin-bottom: 4px; }
.asc-legend { display: inline-flex; align-items: center; gap: 6px; }
.legend-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.asc-trend svg { width: 100%; height: auto; display: block; }
.asc-recent-h { font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.8px; margin: 14px 0 4px; }
.review { padding: 10px 0; border-bottom: 1px solid var(--line); }
.review:last-child { border-bottom: none; }
.review-head { display: flex; justify-content: space-between; font-size: 12px; }
.review-stars { color: var(--accent-2); }
.review-meta { color: var(--muted); }
.review-title { font-weight: 600; margin-top: 4px; }
.review-body { color: var(--muted); font-size: 13px; margin-top: 2px; }

/* Roadmap */
.roadmap-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
.rm-col { background: var(--bg-card-2); border: 1px solid var(--line); border-radius: 8px; padding: 12px; }
.rm-col h3 { margin: 0 0 10px; font-size: 13px; display: flex; justify-content: space-between; }
.rm-count { color: var(--muted); font-weight: normal; }
.rm-col ul { margin: 0; padding: 0; list-style: none; }
.rm-col li { padding: 6px 0; border-bottom: 1px solid var(--line); font-size: 13px; }
.rm-col li:last-child { border-bottom: none; }
.rm-title { display: block; }
.rm-note { display: block; color: var(--muted); font-size: 11px; margin-top: 2px; }
.rm-in_progress h3 { color: var(--accent); }
.rm-upcoming h3 { color: var(--text); }
.rm-blocked h3 { color: var(--warn); }
.rm-completed h3 { color: var(--ok); }

/* Countries */
.ctry-row { display: grid; grid-template-columns: 130px 1fr 60px; align-items: center; gap: 10px; margin-bottom: 4px; font-size: 13px; }
.ctry-bar { height: 6px; background: #0b1220; border-radius: 4px; overflow: hidden; }
.ctry-fill { height: 100%; background: var(--accent); }
.ctry-val { text-align: right; color: var(--muted); }

/* Health chips */
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { font-size: 11px; padding: 4px 10px; border-radius: 12px; border: 1px solid var(--line); background: var(--bg-card-2); }
.chip-ok { color: var(--ok); border-color: rgba(74, 222, 128, 0.3); }
.chip-error { color: var(--err); border-color: rgba(248, 113, 113, 0.3); }
.chip-blocked { color: var(--warn); border-color: rgba(251, 191, 36, 0.3); }
.chip-skipped { color: var(--skipped); }
"""


def render_page(data) -> str:
    gen = data.get("generated_at") or datetime.now(timezone.utc).isoformat()
    return f"""<!doctype html>
<html lang='en'>
<head>
  <meta charset='utf-8'>
  <meta name='viewport' content='width=device-width, initial-scale=1'>
  <meta name='robots' content='noindex'>
  <title>Artemis Tracker — Dashboard</title>
  <style>{CSS}</style>
</head>
<body>
<main>
  <header class='page'>
    <h1>Artemis Tracker — Dashboard</h1>
    <div class='gen'>Generated {esc(gen)}</div>
  </header>

  {section_north_star(data)}
  {section_kpis(data)}
  {section_dau_chart(data)}
  {section_countries(data)}
  {section_newsletter(data)}
  {section_socials(data)}
  {section_app_store(data)}
  {section_subscriptions(data)}
  {section_subscriptions_play(data)}
  {section_push(data)}
  {section_roadmap(data)}
  {section_health(data)}
</main>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", help="Optional JSON file with pre-fetched data")
    ap.add_argument("--out", default=str(DASHBOARD_DIR / "index.html"))
    args = ap.parse_args()

    if args.data and Path(args.data).exists():
        data = json.loads(Path(args.data).read_text())
    else:
        import dashboard_sources
        data = dashboard_sources.fetch_all()

    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)
    DATA_CACHE.write_text(json.dumps(data, indent=2, default=str))
    html_out = render_page(data)
    Path(args.out).write_text(html_out)
    print(f"wrote {args.out} ({len(html_out)} bytes)", file=sys.stderr)
    print(f"wrote {DATA_CACHE} ({DATA_CACHE.stat().st_size} bytes)", file=sys.stderr)


if __name__ == "__main__":
    main()
