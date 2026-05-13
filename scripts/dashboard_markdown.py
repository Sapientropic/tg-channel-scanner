"""Markdown and HTML report artifact rendering for Signal Desk."""

from __future__ import annotations

import html
import re
from pathlib import Path

REPORT_HTML_MOBILE_PATCH = """<style data-dashboard-report-mobile-patch>
@media (max-width: 520px) {
  .report-title {
    max-width: 100% !important;
    font-size: 2.35rem !important;
    line-height: 1.04 !important;
    overflow-wrap: anywhere !important;
    text-shadow: 3px 3px 0 color-mix(in oklch, var(--c-accent) 15%, transparent) !important;
  }
}
@media (max-width: 360px) {
  .report-title { font-size: 2rem !important; }
}
</style>"""


def markdown_inline_html(text: str) -> str:
    escaped = html.escape(text, quote=True)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"__([^_]+)__", r"<em>\1</em>", escaped)

    def link(match: re.Match[str]) -> str:
        label = match.group(1)
        href = html.unescape(match.group(2)).strip()
        if not re.match(r"^https?://", href, flags=re.IGNORECASE):
            return match.group(0)
        return f'<a href="{html.escape(href, quote=True)}" rel="noreferrer" target="_blank">{label}</a>'

    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link, escaped)


def markdown_table_html(lines: list[str]) -> str:
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    if not rows:
        return ""
    has_header = len(rows) > 1 and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in rows[1])
    body_rows = rows[2:] if has_header else rows
    parts = ["<div class=\"table-wrap\"><table>"]
    if has_header:
        parts.append("<thead><tr>")
        parts.extend(f"<th>{markdown_inline_html(cell)}</th>" for cell in rows[0])
        parts.append("</tr></thead>")
    parts.append("<tbody>")
    for row in body_rows:
        parts.append("<tr>")
        parts.extend(f"<td>{markdown_inline_html(cell)}</td>" for cell in row)
        parts.append("</tr>")
    parts.append("</tbody></table></div>")
    return "".join(parts)


def markdown_blocks_html(markdown: str) -> str:
    lines = markdown.splitlines()
    parts: list[str] = []
    index = 0
    in_list = False
    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()
        if not stripped:
            if in_list:
                parts.append("</ul>")
                in_list = False
            index += 1
            continue
        if stripped.startswith("```"):
            if in_list:
                parts.append("</ul>")
                in_list = False
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            parts.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
            continue
        if stripped.startswith("|"):
            if in_list:
                parts.append("</ul>")
                in_list = False
            table_lines: list[str] = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            parts.append(markdown_table_html(table_lines))
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            if in_list:
                parts.append("</ul>")
                in_list = False
            level = len(heading.group(1))
            parts.append(f"<h{level}>{markdown_inline_html(heading.group(2))}</h{level}>")
            index += 1
            continue
        bullet = re.match(r"^[-*]\s+(.+)$", stripped)
        if bullet:
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append(f"<li>{markdown_inline_html(bullet.group(1))}</li>")
            index += 1
            continue
        if in_list:
            parts.append("</ul>")
            in_list = False
        paragraph = [stripped]
        index += 1
        while index < len(lines):
            next_line = lines[index].strip()
            if (
                not next_line
                or next_line.startswith("```")
                or next_line.startswith("|")
                or re.match(r"^(#{1,6})\s+", next_line)
                or re.match(r"^[-*]\s+", next_line)
            ):
                break
            paragraph.append(next_line)
            index += 1
        parts.append(f"<p>{markdown_inline_html(' '.join(paragraph))}</p>")
    if in_list:
        parts.append("</ul>")
    return "\n".join(part for part in parts if part)


def render_markdown_artifact(path: Path) -> bytes:
    markdown = path.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", markdown, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else path.stem.replace("-", " ").title()
    body = markdown_blocks_html(markdown)
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>
    :root {{ color-scheme: light; --ink: #1f2a24; --muted: #5f6d61; --paper: #fff7e8; --line: #d7c7a6; --teal: #1d8f7b; }}
    body {{ margin: 0; background: #f4ecd9; color: var(--ink); font: 16px/1.62 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    main {{ width: min(920px, calc(100% - 28px)); margin: 0 auto; padding: 28px 0 56px; }}
    article {{ background: var(--paper); border: 1px solid var(--line); padding: clamp(18px, 4vw, 38px); box-shadow: 8px 8px 0 rgba(31, 42, 36, 0.12); }}
    h1, h2, h3 {{ line-height: 1.16; margin: 1.45em 0 0.55em; }}
    h1 {{ margin-top: 0; font-size: clamp(2rem, 8vw, 3.4rem); letter-spacing: 0; }}
    h2 {{ border-top: 1px solid var(--line); padding-top: 1.1em; font-size: clamp(1.4rem, 5vw, 2rem); }}
    h3 {{ font-size: 1.15rem; }}
    p, ul, pre, .table-wrap {{ margin: 0 0 1.1rem; }}
    ul {{ padding-left: 1.25rem; }}
    a {{ color: var(--teal); font-weight: 700; }}
    code {{ background: rgba(29, 143, 123, 0.1); padding: 0.1em 0.28em; border-radius: 4px; }}
    pre {{ overflow-x: auto; background: #14251d; color: #d9f5e9; padding: 14px; }}
    .table-wrap {{ overflow-x: auto; border: 1px solid var(--line); }}
    table {{ width: 100%; border-collapse: collapse; min-width: 520px; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 10px 12px; text-align: left; vertical-align: top; }}
    th {{ background: rgba(29, 143, 123, 0.12); font-size: 0.78rem; text-transform: uppercase; }}
    @media (max-width: 560px) {{ main {{ width: calc(100% - 18px); padding-top: 9px; }} article {{ padding: 16px; box-shadow: none; }} body {{ font-size: 15px; }} }}
  </style>
</head>
<body>
  <main><article>{body}</article></main>
</body>
</html>
"""
    return document.encode("utf-8")


def render_html_report_artifact(path: Path) -> bytes:
    document = path.read_text(encoding="utf-8")
    if "data-dashboard-report-mobile-patch" not in document and "</head>" in document:
        document = document.replace("</head>", f"{REPORT_HTML_MOBILE_PATCH}\n</head>", 1)
    return document.encode("utf-8")
