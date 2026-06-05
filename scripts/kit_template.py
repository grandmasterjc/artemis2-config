"""HTML newsletter template for Kit broadcasts.

build_newsletter_html(
    hero_image_url, hero_alt, body_markdown,
    merch_product=None, merch_insert_after_heading=None,
    include_week_ahead_cta=False,
)
returns a complete HTML string ready for the Kit /broadcasts content field.
"""
from __future__ import annotations
import re
from typing import Optional


CSS = """
body { margin:0; padding:0; background:#0b1020; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; color:#e6e9f5; }
.wrap { max-width:600px; margin:0 auto; padding:24px; }
.hero img { width:100%; height:auto; display:block; border-radius:12px; }
h1, h2, h3 { color:#fff; line-height:1.25; }
h1 { font-size:26px; margin:24px 0 8px; }
h2 { font-size:20px; margin:28px 0 8px; }
h3 { font-size:17px; margin:20px 0 6px; }
p { line-height:1.6; font-size:16px; margin:12px 0; color:#cfd4e6; }
a { color:#7fb0ff; }
hr { border:none; border-top:1px solid #2a3050; margin:24px 0; }
.cta { display:inline-block; padding:12px 20px; background:#3a6cff; color:#fff !important; text-decoration:none; border-radius:8px; font-weight:600; }
.merch { background:#161c34; border-radius:12px; padding:16px; margin:24px 0; }
.merch img { width:100%; height:auto; border-radius:8px; display:block; }
.merch .title { font-size:18px; font-weight:600; color:#fff; margin:12px 0 4px; }
.merch .sub { font-size:14px; color:#9aa3c0; margin:0 0 12px; }
.week-ahead { background:#161c34; border-left:3px solid #7fb0ff; padding:14px 18px; margin:24px 0; border-radius:6px; }
.week-ahead h3 { margin:0 0 6px; }
.foot { font-size:13px; color:#7c84a0; margin-top:32px; text-align:center; }
"""


def _md_to_html(md: str) -> str:
    """Tiny markdown subset → HTML. Handles ##/### headings, paragraphs, links, hr."""
    lines = md.split("\n")
    out = []
    para: list[str] = []

    def flush():
        if para:
            text = " ".join(para).strip()
            if text:
                out.append(f"<p>{_inline(text)}</p>")
            para.clear()

    for line in lines:
        s = line.rstrip()
        if not s.strip():
            flush()
            continue
        if s.strip() == "---":
            flush()
            out.append("<hr>")
            continue
        if s.startswith("### "):
            flush()
            out.append(f"<h3>{_inline(s[4:].strip())}</h3>")
            continue
        if s.startswith("## "):
            flush()
            out.append(f"<h2>{_inline(s[3:].strip())}</h2>")
            continue
        if s.startswith("# "):
            flush()
            out.append(f"<h1>{_inline(s[2:].strip())}</h1>")
            continue
        if s.lstrip().startswith("- "):
            flush()
            out.append(f"<p>• {_inline(s.lstrip()[2:])}</p>")
            continue
        para.append(s.strip())
    flush()
    return "\n".join(out)


def _inline(text: str) -> str:
    # [text](url) → <a>
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def _merch_block(product: dict) -> str:
    return f"""
<div class="merch">
  <a href="{product['url']}"><img src="{product['image_url']}" alt="{product.get('title','')}"></a>
  <div class="title">{product.get('title','')}</div>
  <div class="sub">{product.get('subtitle','')}</div>
  <a class="cta" href="{product['url']}">{product.get('cta','Shop')}</a>
</div>
"""


def _week_ahead_block() -> str:
    return """
<div class="week-ahead">
  <h3>Sunday: Week Ahead</h3>
  <p>A short Sunday note with what to watch in the coming week — launches, hearings, expected announcements. Free for all subscribers.</p>
</div>
"""


def build_newsletter_html(
    hero_image_url: str,
    hero_alt: str,
    body_markdown: str,
    merch_product: Optional[dict] = None,
    merch_insert_after_heading: Optional[str] = None,
    include_week_ahead_cta: bool = False,
) -> str:
    body_html = _md_to_html(body_markdown)

    if merch_product:
        merch_html = _merch_block(merch_product)
        if merch_insert_after_heading:
            needle = f"<h2>{merch_insert_after_heading}</h2>"
            if needle in body_html:
                body_html = body_html.replace(needle, needle + merch_html, 1)
            else:
                body_html += merch_html
        else:
            body_html += merch_html

    if include_week_ahead_cta:
        body_html += _week_ahead_block()

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>{CSS}</style></head>
<body><div class="wrap">
<div class="hero"><img src="{hero_image_url}" alt="{hero_alt}"></div>
{body_html}
<div class="foot">
You are receiving this because you subscribed to the Artemis Briefing.<br>
<a href="https://artemis-briefing.kit.com">Manage subscription</a>
</div>
</div></body></html>
"""
