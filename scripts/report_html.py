"""HTML report rendering helpers."""

from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from scripts import report_diagnostics
from scripts.item_display import display_item_title, display_title_parts, meaningful_text
from scripts.profile_schema import ProfileConfig
from scripts.report_markdown import action_for_rating, field_label, table_value
from scripts.report_models import ReportError, ReportResult
from scripts.report_sources import (
    as_list,
    build_message_lookup,
    decision_status,
    decision_status_label,
    merge_unique,
    normalize_rating,
    raw_texts_for_job,
    sort_items_for_report,
    source_refs_for_job,
)

# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
SHARED_CSS_NAME = "report-shared.css"
SHARED_JS_NAME = "report-theme.js"


def _read_template_asset(name: str) -> str:
    path = TEMPLATE_DIR / name
    if not path.exists():
        raise ReportError(f"HTML template asset not found: {path}")
    return path.read_text(encoding="utf-8")


def _action_for_rating(item: dict, rating: str, profile_config: ProfileConfig | None = None) -> str:
    return action_for_rating(item, rating, profile_config)


def _load_icon_b64(job_mode: bool = True) -> str:
    shared_icon = TEMPLATE_DIR / "icon-report.png"
    if shared_icon.exists():
        icon_path = shared_icon
    else:
        icon_name = "icon-job.png" if job_mode else "icon-generic.png"
        icon_path = TEMPLATE_DIR / icon_name
        if not icon_path.exists():
            fallback = TEMPLATE_DIR / "icon-job.png"
            if fallback.exists():
                icon_path = fallback
            else:
                return ""
    import base64
    return base64.b64encode(icon_path.read_bytes()).decode("ascii")


def _esc(text: str) -> str:
    return html.escape(str(text), quote=True)


SAFE_LINK_REL = "noopener noreferrer"
SAFE_HREF_SCHEMES = {"http", "https", "mailto"}
UNSAFE_HREF_CHAR_RE = re.compile(r"""[\x00-\x20"'<>`]""")
TELEGRAM_HANDLE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")
EMAIL_RE = re.compile(r"^[^@\s<>]+@[^@\s<>]+\.[^@\s<>]+$")


def safe_href(value: object) -> str | None:
    """Return an escaped href attribute value, or None when it is not safe.

    Reports are built from Telegram text and LLM output, so link validation must
    happen before attribute escaping. In particular, quotes and whitespace are
    rejected instead of merely escaped because they usually indicate attribute
    injection attempts or pasted prose rather than a navigable URL.
    """
    href = str(value or "").strip()
    if not href or UNSAFE_HREF_CHAR_RE.search(href):
        return None
    parsed = urlparse(href)
    scheme = parsed.scheme.lower()
    if scheme not in SAFE_HREF_SCHEMES:
        return None
    if scheme in {"http", "https"} and not parsed.netloc:
        return None
    if scheme == "mailto":
        address = parsed.path
        if not EMAIL_RE.fullmatch(address):
            return None
    return html.escape(href, quote=True)


def telegram_handle_to_url(value: object) -> str | None:
    handle = str(value or "").strip()
    if handle.startswith("@"):
        handle = handle[1:]
    if not TELEGRAM_HANDLE_RE.fullmatch(handle):
        return None
    return f"https://t.me/{handle}"


def _safe_link_html(href: object, label: object, *, label_is_html: bool = False) -> str | None:
    safe = safe_href(href)
    if safe is None:
        return None
    label_html = str(label) if label_is_html else _esc(label)
    return (
        f'<a href="{safe}" target="_blank" '
        f'rel="{SAFE_LINK_REL}">{label_html}</a>'
    )


def _link_or_text(href: object, label: object, *, label_is_html: bool = False) -> str:
    link = _safe_link_html(href, label, label_is_html=label_is_html)
    if link:
        return link
    return str(label) if label_is_html else _esc(label)


def readable_url_label(value: object, *, field_name: str = "") -> str:
    parsed = urlparse(str(value or "").strip())
    field = field_name.lower()
    if field == "origin_url":
        return "Open source"
    if parsed.netloc:
        host = parsed.netloc.removeprefix("www.")
        path = parsed.path.strip("/")
        label = host if not path else f"{host}/{path.split('/')[0]}"
        return label[:34] + "..." if len(label) > 37 else label
    return "Open link"


def missing_url_label(field_name: str) -> str:
    field = field_name.lower()
    if field in {"apply_url", "application_url"}:
        return "No apply link found"
    return "No link found"


def _url_field_html(field_name: str, values: list[str]) -> str:
    rendered: list[str] = []
    for value in _split_inline_values(values):
        text = str(value or "").strip()
        if safe_href(text):
            rendered.append(_link_or_text(text, readable_url_label(text, field_name=field_name)))
        elif not text or text.lower() in {"not specified", "unknown", "none", "n/a"}:
            rendered.append(_esc(missing_url_label(field_name)))
        else:
            rendered.append(_esc(f"{missing_url_label(field_name)}: {text}"))
    return _inline_html_group(rendered)


def _tg_md_to_html(text: str) -> str:
    """Convert Telegram-flavored markdown to safe HTML snippets.

    Handles: **bold**, __italic__, `code`, [link](url), https://urls.
    Everything else is HTML-escaped first, then patterns are restored.
    """
    # Escape first
    s = html.escape(text, quote=True)

    # Restore **bold**
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    # Restore __italic__
    s = re.sub(r"__(.+?)__", r"<em>\1</em>", s)
    # Restore `code`
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    # Restore [text](url)
    def _replace_md_link(match: re.Match[str]) -> str:
        label_html = match.group(1)
        href = html.unescape(match.group(2))
        return _link_or_text(href, label_html, label_is_html=True)

    s = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        _replace_md_link,
        s,
    )
    # Bare URLs
    def _replace_bare_url(match: re.Match[str]) -> str:
        label_html = match.group(1)
        href = html.unescape(label_html)
        return _link_or_text(href, label_html, label_is_html=True)

    s = re.sub(
        r"(?<!href=\")(https?://[^\s<\)]+)",
        _replace_bare_url,
        s,
    )
    # Newlines → <br>
    s = s.replace("\n", "<br>\n")
    return s


def _channel_link(name: str) -> str:
    name = name.strip()
    telegram_url = telegram_handle_to_url(name)
    if telegram_url:
        return _link_or_text(telegram_url, name)
    if safe_href(name):
        return _link_or_text(name, name)
    return _esc(name)


def _source_links(sources: object) -> str:
    return _inline_html_group([_channel_link(s) for s in _split_inline_values(as_list(sources))])


def _inline_html_group(items: list[str]) -> str:
    cleaned = [item for item in items if item]
    if len(cleaned) <= 1:
        return cleaned[0] if cleaned else ""
    return (
        '<span class="inline-ref-list">'
        + "".join(f'<span class="inline-ref">{item}</span>' for item in cleaned)
        + "</span>"
    )


def _split_inline_values(values: list[str]) -> list[str]:
    """Split legacy report values that used spaced slashes as UI separators.

    Fields like contact/source/link can arrive from older Markdown reports as one
    display string ("Not specified / @handle"). Splitting only at the renderer keeps
    parsing stable while removing the visual slash artifact from the card middle.
    """
    parts = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        if " / " in text and not safe_href(text):
            parts.extend(part.strip() for part in text.split(" / ") if part.strip())
        else:
            parts.append(text)
    return parts


def _contact_html(contact: str) -> str:
    contact = str(contact).strip()
    if not contact or contact in ("Not specified", "Unknown"):
        return _esc(contact)
    if contact.startswith("@"):
        telegram_url = telegram_handle_to_url(contact)
        return _link_or_text(telegram_url, contact) if telegram_url else _esc(contact)
    if EMAIL_RE.fullmatch(contact):
        return _link_or_text(f"mailto:{contact}", contact)
    if contact.startswith(("http://", "https://")):
        # Shorten URL display: show domain + /... for long URLs
        parsed = urlparse(contact)
        display = parsed.netloc or "link"
        return _link_or_text(contact, display)
    return _esc(contact)


def _render_profile_items(profile: str) -> str:
    lines = []
    for raw in profile.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("```"):
            continue
        if line.lower().startswith("## search rules"):
            break
        if line.startswith("- **"):
            parts = line[2:].split("**", 2)
            if len(parts) >= 3:
                key = parts[1].strip(": ")
                val = parts[2].strip()
                lines.append(
                    f'      <div class="profile-item">'
                    f'<span class="profile-key">{_esc(key)}</span>'
                    f'<span class="profile-val">{_esc(val)}</span></div>'
                )
    return "\n".join(lines)


def build_report_id(meta: dict | None, profile: str) -> str:
    date = (meta or {}).get("scan_date") or datetime.now(UTC).date().isoformat()
    basis = json.dumps(
        {
            "date": date,
            "started_at": (meta or {}).get("scan_started_at", ""),
            "channel_list": (meta or {}).get("channel_list_path", ""),
            "profile": profile[:240],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:10]
    return f"tgcs-{date}-{digest}"


def _data_json(value: object) -> str:
    return html.escape(json.dumps(value, ensure_ascii=False, separators=(",", ":")), quote=True)


def _feedback_attrs(item: dict, item_title: str, message_lookup: dict | None) -> str:
    payload = {"source_message_refs": source_refs_for_job(item, message_lookup)}
    basis = json.dumps({"title": item_title, "refs": payload["source_message_refs"]}, ensure_ascii=False, sort_keys=True)
    card_key = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]
    return (
        'data-feedback-card '
        f'data-feedback-card-id="{card_key}" '
        f'data-item-title="{_esc(item_title)}" '
        f'data-feedback-payload="{_data_json(payload)}"'
    )


def _feedback_controls() -> str:
    return """
      <div class="feedback-controls" aria-label="Local feedback">
        <span class="feedback-label">Feedback</span>
        <button type="button" data-feedback-value="keep">Keep</button>
        <button type="button" data-feedback-value="skip">Skip</button>
        <button type="button" data-feedback-value="false_positive">False positive</button>
        <button type="button" data-feedback-undo>Undo</button>
      </div>"""


def _render_feedback_panel() -> str:
    return """
  <section class="feedback-panel" aria-label="Local report feedback">
    <h2 class="feedback-title">Feedback</h2>
    <p class="feedback-copy">Feedback stays in this browser until you export JSONL.</p>
    <div class="feedback-note-row">
      <textarea data-feedback-note rows="3" placeholder="Missed item, false negative, or short note"></textarea>
      <button type="button" data-feedback-false-negative>Add false negative</button>
    </div>
    <div class="feedback-actions">
      <button type="button" data-feedback-export>Export JSONL</button>
      <button type="button" data-feedback-clear>Clear report feedback</button>
      <output data-feedback-status aria-live="polite"></output>
    </div>
  </section>"""


def _decision_badge(item: dict) -> str:
    label = decision_status_label(item)
    status = decision_status(item)
    if not label:
        return ""
    return f'<span class="decision-state-badge {status}">{_esc(label)}</span>'


def _decision_explanation_html(item: dict) -> str:
    state = item.get("decision_state")
    if not isinstance(state, dict):
        return ""
    explanations = state.get("explanations") if isinstance(state.get("explanations"), dict) else {}
    rows = []
    for key in ("novelty", "match_confidence", "urgency", "source_priority", "negative_evidence"):
        value = explanations.get(key)
        if value in (None, "", []):
            continue
        label = key.replace("_", " ").title()
        rows.append(
            f'<div class="decision-factor"><span>{_esc(label)}</span><strong>{_esc(table_value(value))}</strong></div>'
        )
    if not rows:
        return ""
    return f'<div class="decision-factors">{"".join(rows)}</div>'


def _render_generic_card(
    item: dict,
    index: int,
    message_lookup: dict | None = None,
    profile_config: ProfileConfig | None = None,
) -> str:
    rating = normalize_rating(item.get("rating"))
    action = _action_for_rating(item, rating, profile_config)
    dedup_fields = (profile_config.mode.dedup_fields if profile_config else None) or ["company", "role"]

    name_text, subtitle_text = display_title_parts(
        item,
        dedup_fields=dedup_fields,
        fallback="Unknown item",
    )
    name = _esc(name_text)
    subtitle = _esc(subtitle_text)

    # Build detail grid from profile field definitions
    detail_rows = []
    if profile_config:
        for f in profile_config.mode.fields:
            if (
                f.name in ("source_message_refs", "source_message_ids", "rating", "action", "why")
                or f.name in dedup_fields[:2]
            ):
                continue
            val = item.get(f.name)
            if val is None:
                val = "Not specified"
            if isinstance(val, list):
                val_list = [str(v) for v in val if v]
            else:
                val_list = None

            # Special rendering for contact/link/source fields
            if f.name == "contact":
                values = val_list or [str(val)]
                rendered = _inline_html_group([_contact_html(c) for c in _split_inline_values(values)])
            elif f.name == "source" and val_list:
                rendered = _source_links(val_list)
            elif f.name == "link":
                values = val_list or [str(val)]
                rendered = _url_field_html(f.name, values)
            elif f.name == "url" or f.name.endswith("_url"):
                values = val_list or [str(val)]
                rendered = _url_field_html(f.name, values)
            else:
                display = ", ".join(str(v) for v in val_list) if val_list else str(val)
                rendered = _esc(display)

            detail_rows.append(
                f'<div class="item-detail"><span class="item-detail-key">{_esc(field_label(f.name))}</span>'
                f'<span class="item-detail-value">{rendered}</span></div>'
            )

    detail_block = "\n        ".join(detail_rows) or ""
    why = item.get("why") or ""
    stack = item.get("stack") or []
    concerns = item.get("concerns") or []
    tags = "\n".join(f'<li class="tag">{_esc(t)}</li>' for t in stack)
    concern_items = "\n".join(f"<li>{_esc(c)}</li>" for c in concerns)

    raw_texts = raw_texts_for_job(item, message_lookup)

    raw_section = ""
    if raw_texts:
        parts = []
        for ch, text in raw_texts:
            parts.append(f'<span class="channel-label">{_esc(ch)}</span>' + _tg_md_to_html(text))
        raw_html = '<hr class="raw-divider">'.join(parts)
        raw_section = f"""
      <button class="raw-toggle" type="button" aria-expanded="false"><span class="arrow">&#9654;</span> <span class="label">View original</span></button>
      <div class="raw-content"><div class="raw-content-inner"><div class="raw-content-body">{raw_html}</div></div></div>"""

    subtitle_html = f'\n        <span class="item-subtitle">— {subtitle}</span>' if subtitle else ""
    detail_block_html = f"""<div class="item-details">
        {detail_block}
      </div>""" if detail_block else ""

    item_title = display_item_title(item, dedup_fields=dedup_fields, fallback="Unknown item")

    return f"""
    <article class="item-card {rating}" {_feedback_attrs(item, item_title, message_lookup)}>
      <div class="item-card-head">
        <div>
          <div class="item-number">Dispatch {index:02d}</div>
          <div class="item-title-row">
            <span class="item-name">{name}</span>{subtitle_html}
          </div>
        </div>
        <span class="item-action {rating}">{_esc(action)}</span>
      </div>
      {_decision_badge(item)}
      {detail_block_html}
      <div class="item-notes"><strong>Why:</strong> {_esc(why)}</div>
      {_decision_explanation_html(item)}
      {f'<ul class="tag-list">{tags}</ul>' if stack else ''}
      {f'<ul class="concern-list">{concern_items}</ul>' if concerns else ''}
      {raw_section}
      {_feedback_controls()}
    </article>"""


def _render_job_card(
    job: dict,
    index: int,
    message_lookup: dict | None = None,
    profile_config: ProfileConfig | None = None,
) -> str:
    rating = normalize_rating(job.get("rating"))
    heading_role, heading_company = display_title_parts(
        job,
        dedup_fields=["company", "role"],
        fallback="Unknown role",
    )
    location = table_value(job.get("location"))
    salary = table_value(job.get("salary"))
    contacts = merge_unique(job.get("contacts", []), as_list(job.get("contact")))
    links = merge_unique(job.get("links", []), as_list(job.get("link")))
    sources = as_list(job.get("sources")) or as_list(job.get("source"))
    why = job.get("why") or ""
    stack = job.get("stack") or []
    concerns = job.get("concerns") or []
    origin_url = job.get("origin_url", "")
    origin_channel = job.get("origin_channel", "")
    action = _action_for_rating(job, rating, profile_config)

    contact_val = _inline_html_group(
        [
            _contact_html(c)
            for c in _split_inline_values(contacts or links or [job.get("contact") or "Not specified"])
        ]
    )

    raw_texts = raw_texts_for_job(job, message_lookup)

    raw_section = ""
    if raw_texts:
        parts = []
        for ch, text in raw_texts:
            parts.append(f'<span class="channel-label">{_esc(ch)}</span>' + _tg_md_to_html(text))
        raw_html = '<hr class="raw-divider">'.join(parts)

        # Embed origin info inside the expandable panel
        origin_footer = ""
        if origin_url or origin_channel:
            origin_bits = []
            if origin_channel:
                origin_bits.append(f'Forwarded from <strong>{_esc(origin_channel)}</strong>')
            if origin_url:
                origin_link = _safe_link_html(origin_url, "Open in Telegram")
                if origin_link:
                    origin_bits.append(origin_link)
            if origin_bits:
                origin_footer = f'<div class="raw-origin">{" &middot; ".join(origin_bits)}</div>'

        raw_section = f"""
      <button class="raw-toggle" type="button" aria-expanded="false"><span class="arrow">&#9654;</span> <span class="label">View original</span></button>
      <div class="raw-content"><div class="raw-content-inner"><div class="raw-content-body">{raw_html}{origin_footer}</div></div></div>"""

    # Fallback: no raw text matched, show origin link standalone
    origin_line = ""
    if not raw_section and (origin_url or origin_channel):
        origin_parts = []
        if origin_channel:
            origin_parts.append(f'Forwarded from <strong>{_esc(origin_channel)}</strong>')
        if origin_url:
            origin_link = _safe_link_html(origin_url, "Open in Telegram")
            if origin_link:
                origin_parts.append(origin_link)
        if origin_parts:
            origin_line = f'<div class="job-origin">{" &middot; ".join(origin_parts)}</div>'

    tags = "\n".join(f'<li class="tag">{_esc(t)}</li>' for t in stack)
    concern_items = "\n".join(f"<li>{_esc(c)}</li>" for c in concerns)

    item_title = display_item_title(job, dedup_fields=["company", "role"], fallback="Unknown item")
    company_title_html = (
        f'\n            <span class="job-company">— {_esc(heading_company)}</span>'
        if meaningful_text(heading_company)
        else ""
    )

    return f"""
    <article class="job-card {rating}" {_feedback_attrs(job, item_title, message_lookup)}>
      <div class="job-card-head">
        <div>
          <div class="job-number">Dispatch {index:02d}</div>
          <div class="job-title-row">
            <span class="job-role">{_esc(heading_role)}</span>{company_title_html}
          </div>
        </div>
        <span class="job-action {rating}">{_esc(action)}</span>
      </div>
      {_decision_badge(job)}
      <div class="job-details">
        <div class="job-detail"><span class="job-detail-key">Location</span><span class="job-detail-value">{_esc(location)}</span></div>
        <div class="job-detail"><span class="job-detail-key">Salary</span><span class="job-detail-value">{_esc(salary)}</span></div>
        <div class="job-detail"><span class="job-detail-key">Contact</span><span class="job-detail-value">{contact_val}</span></div>
        <div class="job-detail"><span class="job-detail-key">Source</span><span class="job-detail-value">{_source_links(sources)}</span></div>
      </div>
      <div class="job-extras"><strong>Why:</strong> {_esc(why)}</div>
      {_decision_explanation_html(job)}
      {f'<ul class="tag-list">{tags}</ul>' if stack else ''}
      {f'<ul class="concern-list">{concern_items}</ul>' if concerns else ''}
      {raw_section}{origin_line}
      {_feedback_controls()}
    </article>"""


def render_html(
    result: ReportResult,
    profile: str,
    meta: dict | None,
    args,
    messages: list[dict] | None = None,
    profile_config: ProfileConfig | None = None,
) -> str:
    # Select template by mode: job → report-job.html, custom → report-generic.html
    is_job = not profile_config or profile_config.mode.mode == "job"
    template_name = "report-job.html" if is_job else "report-generic.html"
    template_path = TEMPLATE_DIR / template_name
    if not template_path.exists():
        raise ReportError(f"HTML template not found: {template_path}")

    template = template_path.read_text(encoding="utf-8")
    shared_css = _read_template_asset(SHARED_CSS_NAME)
    shared_js = _read_template_asset(SHARED_JS_NAME)
    icon_b64 = _load_icon_b64(job_mode=is_job)

    message_lookup = build_message_lookup(messages)

    date = (meta.get("scan_date") if meta else None) or datetime.now(UTC).date().isoformat()
    scan_window = (meta.get("scan_window") if meta else None) or "Unknown"
    channel_count = (meta.get("channel_count") if meta else None) or "?"
    total_messages = (meta.get("total_messages_collected") if meta else None) or "?"

    stats = result.stats

    high_jobs = sort_items_for_report([j for j in _get_jobs_from_result(result) if normalize_rating(j.get("rating")) == "high"])
    medium_jobs = sort_items_for_report([j for j in _get_jobs_from_result(result) if normalize_rating(j.get("rating")) == "medium"])
    low_jobs = sort_items_for_report([j for j in _get_jobs_from_result(result) if normalize_rating(j.get("rating")) == "low"])

    sections = []
    idx = 1
    labels = profile_config.labels if profile_config else None
    render_card = _render_generic_card if not is_job else _render_job_card
    section_class = "item-section" if not is_job else "job-section"

    for rating_group, label, css_class in [
        (high_jobs, labels.section_high if labels else "Highly Recommended", "high"),
        (medium_jobs, labels.section_medium if labels else "Worth Investigating", "medium"),
        (low_jobs, labels.section_low if labels else "Low Priority", "low"),
    ]:
        cards = ""
        if rating_group:
            for job in rating_group:
                cards += render_card(job, idx, message_lookup, profile_config)
                idx += 1
        else:
            cards = '<div class="empty-state">No matches.</div>'
        sections.append(
            f'  <section class="{section_class}">\n'
            f'    <h2 class="section-heading {css_class}"><span class="section-dot"></span>{label}</h2>\n'
            f'{cards}\n'
            f'  </section>'
        )

    profile_items = _render_profile_items(profile)
    footer_note = args.next_scan_note if hasattr(args, "next_scan_note") else ""
    report_id = build_report_id(meta, profile)
    diagnostics_panel = report_diagnostics.render_html(result.diagnostics or [])
    feedback_panel = _render_feedback_panel()

    if is_job:
        # job template: original hardcoded format, only standard placeholders
        return template.format(
            shared_css=shared_css,
            shared_js=shared_js,
            icon_b64=icon_b64,
            date=date,
            scan_window=scan_window,
            channel_count=channel_count,
            total_messages=total_messages,
            stat_matches=stats["matches"],
            stat_high=stats["high"],
            stat_medium=stats["medium"],
            stat_low=stats["low"],
            stat_deduped=stats["duplicates_removed"],
            profile_items=profile_items,
            sections="\n\n".join(sections),
            footer_note=f" {_esc(footer_note)}" if footer_note else "",
            report_id=_esc(report_id),
            profile_label="Job Scan Report",
            diagnostics_panel=diagnostics_panel,
            feedback_panel=feedback_panel,
        )

    # generic template: all labels driven by profile_config
    labels = profile_config.labels if profile_config else None
    report_title = labels.report_title if labels else "Scan Report"
    profile_section_title = labels.profile_section_title if labels else "Profile"
    methodology_label = labels.methodology_label if labels else "Telegram channels"
    action_high = (profile_config.actions.high if profile_config else None) or "Act"
    action_medium = (profile_config.actions.medium if profile_config else None) or "Review"
    action_low = (profile_config.actions.low if profile_config else None) or "Skip"

    return template.format(
        shared_css=shared_css,
        shared_js=shared_js,
        icon_b64=icon_b64,
        date=date,
        scan_window=scan_window,
        channel_count=channel_count,
        total_messages=total_messages,
        report_title=_esc(report_title),
        profile_section_title=_esc(profile_section_title),
        methodology_label=_esc(methodology_label),
        stat_matches=stats["matches"],
        stat_high=stats["high"],
        stat_medium=stats["medium"],
        stat_low=stats["low"],
        stat_deduped=stats["duplicates_removed"],
        label_high=_esc(action_high),
        label_medium=_esc(action_medium),
        label_low=_esc(action_low),
        profile_items=profile_items,
        sections="\n\n".join(sections),
        footer_note=f" {_esc(footer_note)}" if footer_note else "",
        report_id=_esc(report_id),
        profile_label=_esc(report_title),
        diagnostics_panel=diagnostics_panel,
        feedback_panel=feedback_panel,
    )


def _get_jobs_from_result(result: ReportResult) -> list[dict]:
    return result.jobs or []
