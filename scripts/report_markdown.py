"""Markdown report rendering and report assembly helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from scripts import decision_intelligence, report_diagnostics
from scripts.item_display import display_item_title
from scripts.profile_schema import ProfileConfig, parse_profile_config
from scripts.report_models import ReportResult
from scripts.report_sources import (
    as_list,
    build_source_summary,
    deduplicate_jobs,
    decision_status_label,
    merge_unique,
    normalize_rating,
    rating_counts,
    sort_items_for_report,
)


_DEFAULT_ACTIONS = {"high": "Apply", "medium": "Inspect", "low": "Skip unless criteria change"}


def _default_labels():
    """Lazy import to avoid circular dependency."""
    from scripts.profile_schema import ReportLabels
    return ReportLabels()


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if text:
                rows.append(json.loads(text))
    return rows


def infer_meta_path(input_path: Path) -> Path:
    return input_path.with_suffix(".meta.json")


def load_meta(input_path: Path, explicit_meta: str | None = None) -> dict | None:
    path = Path(explicit_meta) if explicit_meta else infer_meta_path(input_path)
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def profile_summary(profile: str, is_job_mode: bool = True) -> str:
    lines: list[str] = []
    in_code_block = False
    for raw in profile.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block or not line:
            continue
        # Stop at mode-specific sections (not part of the summary)
        if line.lower().startswith("## search rules") or line.lower().startswith("## extraction "):
            break
        if line.lower().startswith("## report labels"):
            break
        if line.startswith("#"):
            text = line.lstrip("#").strip()
            if text.lower().startswith("candidate profile") or text.lower().startswith("monitor:"):
                continue
            lines.append(f"- **Profile**: {text}")
        elif line.startswith("- "):
            lines.append(line)
        if len(lines) >= 8:
            break
    return "\n".join(lines) if lines else profile.strip()


def table_value(value: object) -> str:
    if isinstance(value, list):
        text = " / ".join(str(item) for item in value if item not in (None, ""))
    else:
        text = str(value or "Not specified")
    return text.replace("|", "\\|").replace("\n", " ").strip() or "Not specified"


def field_label(name: str) -> str:
    special = {"negative_evidence": "Negative evidence"}
    if name in special:
        return special[name]
    acronyms = {"url": "URL", "id": "ID", "ids": "IDs", "api": "API", "llm": "LLM", "ocr": "OCR"}
    parts = str(name or "").replace("_", " ").split()
    return " ".join(acronyms.get(part.casefold(), part.capitalize()) for part in parts)


def bullet_list(items: list[str]) -> str:
    if not items:
        return "- Not specified"
    return "\n".join(f"- {item}" for item in items)


def action_for_rating(item: dict, rating: str, profile_config: ProfileConfig | None = None) -> str:
    explicit = item.get("action")
    if explicit:
        return str(explicit)
    if profile_config:
        value = getattr(profile_config.actions, rating, None)
        if value:
            return str(value)
    return _DEFAULT_ACTIONS[rating]


def render_job(job: dict, index: int, profile_config: ProfileConfig | None = None) -> str:
    # Title: use the same placeholder-aware display logic as dashboard cards.
    dedup_fields = (profile_config.mode.dedup_fields if profile_config else None) or ["company", "role"]
    title = display_item_title(job, dedup_fields=dedup_fields, fallback="Unknown item")

    contacts = merge_unique(job.get("contacts", []), as_list(job.get("contact")))
    links = merge_unique(job.get("links", []), as_list(job.get("link")))
    contact_value = contacts or links or [job.get("contact") or job.get("link") or "Not specified"]
    sources = job.get("sources") or as_list(job.get("source"))

    rating = normalize_rating(job.get("rating"))
    action = action_for_rating(job, rating, profile_config)
    state_label = decision_status_label(job)

    # Build table rows from profile fields (custom) or hardcoded (job default)
    if profile_config and profile_config.mode.mode != "job":
        field_defs = profile_config.mode.fields
        table_rows = []
        for f in field_defs:
            if f.name in ("source_message_refs", "source_message_ids", "rating", "action"):
                continue
            val = job.get(f.name)
            if f.name == "contact":
                val = contact_value
            elif f.name == "source":
                val = sources
            label = field_label(f.name)
            table_rows.append(f"| **{label}** | {table_value(val)} |")
        table_block = "\n".join(table_rows) or "| **Item** | See details above |"
    else:
        table_block = f"""| **Company** | {table_value(job.get("company"))} |
| **Role** | {table_value(job.get("role"))} |
| **Location** | {table_value(job.get("location"))} |
| **Salary** | {table_value(job.get("salary"))} |
| **Contact** | {table_value(contact_value)} |
| **Source** | {table_value(sources)} |"""
    state_block = f"\n**Decision state: {state_label}**\n" if state_label else ""
    negative_evidence = job.get("negative_evidence")
    negative_block = (
        f"\n**Negative evidence**: {table_value(negative_evidence)}\n"
        if negative_evidence and not (profile_config and profile_config.mode.mode != "job")
        else ""
    )

    return f"""### {index}. {title}

| Field | Detail |
|-------|--------|
{table_block}

**Why it matches**: {job.get("why") or "Not specified"}

**Stack required**:
{bullet_list(job.get("stack") or [])}

**Concerns**:
{bullet_list(job.get("concerns") or [])}

**Action**: **{action}**
{state_block}{negative_block}
"""


def render_group(title: str, jobs: list[dict], start_index: int, profile_config: ProfileConfig | None = None) -> tuple[str, int]:
    if not jobs:
        return f"## {title}\n\nNo matches.\n", start_index
    chunks = [f"## {title}\n"]
    index = start_index
    for job in jobs:
        chunks.append(render_job(job, index, profile_config))
        index += 1
    return "\n---\n\n".join(chunks), index


def build_report(
    *,
    messages: list[dict],
    profile: str,
    raw_jobs: list[dict],
    meta: dict | None,
    next_scan_note: str | None = None,
    considered_message_count: int | None = None,
    profile_config: ProfileConfig | None = None,
    source_registry: dict | None = None,
    state: dict | None = None,
    feedback_entries: list[dict] | None = None,
    state_observed_at: str | None = None,
) -> ReportResult:
    dedup_fields = profile_config.mode.dedup_fields if profile_config else None
    jobs, duplicates_removed = deduplicate_jobs(raw_jobs, messages, dedup_fields)
    state_summary = None
    if state is not None:
        observed_at = state_observed_at or (str(meta.get("scan_date")) if meta and meta.get("scan_date") else None)
        jobs, state, state_summary = decision_intelligence.enrich_items(
            jobs,
            profile=profile,
            profile_config=profile_config or parse_profile_config(profile),
            state=state,
            feedback_entries=feedback_entries or [],
            observed_at=observed_at,
            source_registry=source_registry,
        )
    diagnostics = report_diagnostics.build_diagnostics(
        messages=messages,
        raw_items=raw_jobs,
        meta=meta,
        ocr_enabled=bool(meta.get("ocr_enabled")) if meta else False,
        llm_available=True,
    )
    counts = rating_counts(jobs)
    total_messages = (
        int(meta["total_messages_collected"])
        if meta and isinstance(meta.get("total_messages_collected"), int)
        else len(messages)
    )
    stats = {
        "total_messages_scanned": total_messages,
        "messages_considered": considered_message_count or len(messages),
        "raw_relevant_candidates": len(raw_jobs),
        "matches": len(jobs),
        "high": counts["high"],
        "medium": counts["medium"],
        "low": counts["low"],
        "duplicates_removed": duplicates_removed,
        "non_relevant_filtered_out": max(
            0, (considered_message_count or len(messages)) - len(raw_jobs)
        ),
    }
    warnings: list[str] = []
    if meta is None:
        warnings.append("⚠️ Needs confirmation: scan metadata sidecar was not found; header stats are inferred from JSONL only.")

    scan_date = meta.get("scan_date") if meta else datetime.now(UTC).date().isoformat()
    scan_window = meta.get("scan_window") if meta else "Unknown scan window"
    channel_count = meta.get("channel_count") if meta else "Unknown"
    channels = meta.get("channels", []) if meta else []
    channel_hint = ""
    if channels:
        preview = ", ".join(str(channel) for channel in channels[:5])
        if len(channels) > 5:
            preview += ", etc."
        channel_hint = f" ({preview})"

    labels = profile_config.labels if profile_config else None
    is_job = (profile_config.mode.mode == "job") if profile_config else True

    high_jobs = sort_items_for_report([job for job in jobs if normalize_rating(job.get("rating")) == "high"])
    medium_jobs = sort_items_for_report([job for job in jobs if normalize_rating(job.get("rating")) == "medium"])
    low_jobs = sort_items_for_report([job for job in jobs if normalize_rating(job.get("rating")) == "low"])

    high_section, next_index = render_group(
        (labels or _default_labels()).section_high, high_jobs, 1, profile_config
    )
    medium_section, next_index = render_group(
        (labels or _default_labels()).section_medium, medium_jobs, next_index, profile_config
    )
    low_section, _ = render_group(
        (labels or _default_labels()).section_low, low_jobs, next_index, profile_config
    )
    warning_block = "\n".join(warnings)
    if warning_block:
        warning_block = f"\n{warning_block}\n"
    diagnostic_block = report_diagnostics.render_markdown(diagnostics)
    if diagnostic_block:
        diagnostic_block = f"\n{diagnostic_block}\n---\n"

    footer = "*Generated automatically.*"
    if next_scan_note:
        footer = f"*Generated automatically. {next_scan_note}*"

    report_title = (labels or _default_labels()).report_title
    profile_title = (labels or _default_labels()).profile_section_title
    stats_label = (labels or _default_labels()).stats_label
    methodology_label = (labels or _default_labels()).methodology_label
    dedup_desc = "Same normalized " + " + ".join(
        f"**{f}**" for f in (dedup_fields or ["company", "role"])
    ) + " treated as one entry regardless of source channel."
    feedback_schema = json.dumps(
        {
            "schema_version": "v1",
            "created_at": "2026-05-06T09:00:00Z",
            "report_id": "report-id",
            "profile_label": "profile",
            "source_message_refs": [{"channel": "channel", "id": 123}],
            "feedback": "keep",
            "note": "",
            "item_title": "item title",
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )

    markdown = f"""# {report_title} -- Telegram Channels

**Date**: {scan_date}
**Scan window**: {scan_window}
**Channels scanned**: {channel_count}{channel_hint}
**Total messages processed**: {stats["total_messages_scanned"]}
**Matches found**: {stats["matches"]} (after deduplication)
{warning_block}
---

## {profile_title}

{profile_summary(profile, is_job_mode=is_job)}

---

{diagnostic_block}

{high_section}

---

{medium_section}

---

{low_section}

---

## Statistics

| Category | Count |
|----------|-------|
| Total messages scanned | {stats["total_messages_scanned"]} |
| {stats_label} | {stats["matches"]} |
| High match (apply) | {stats["high"]} |
| Medium match (inspect) | {stats["medium"]} |
| Low match (conditional) | {stats["low"]} |
| Duplicates removed | {stats["duplicates_removed"]} |
| Non-relevant filtered out | {stats["non_relevant_filtered_out"]} |

---

## Methodology

- **Sources**: {channel_count} {methodology_label}, messages from {scan_window}
- **Filtering**: LLM extracts listings against the supplied profile; program logic renders the final report.
- **Deduplication**: {dedup_desc}
- **Matching criteria**: Based on the supplied profile and preferences.

---

## Feedback

HTML reports let you mark `keep`, `skip`, and `false_positive` locally, then export
JSONL. For Markdown-only workflows, append one JSON object per line with this v1
schema:

```json
{feedback_schema}
```

Use `false_negative` with an empty `source_message_refs` list when the report missed
something that should have appeared.

---

{footer}
"""
    return ReportResult(
        markdown=markdown,
        stats=stats,
        warnings=warnings,
        diagnostics=diagnostics,
        jobs=jobs,
        source_summary=build_source_summary(jobs, messages, meta, source_registry),
        state_summary=state_summary,
        state=state,
    )
