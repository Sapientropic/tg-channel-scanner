"""Profile creation helpers for Signal Desk."""

from __future__ import annotations

import base64
import io
import json
import re
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts import monitor_config, monitor_state


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DESK_DELIVERY_TARGET_ID = "telegram-bot-default"
PROFILE_CREATE_ALLOWED_FIELDS = {"brief", "source_filename", "source_text", "source_base64"}
PROFILE_CREATE_MAX_TEXT_LENGTH = 30000
PROFILE_CREATE_MAX_BINARY_BYTES = 4 * 1024 * 1024


def _facade_attr(name: str, default: Any) -> Any:
    facade = sys.modules.get("scripts.dashboard_server")
    return getattr(facade, name, default) if facade is not None else default


def _facade_callable(name: str, default: Any) -> Any:
    helper = _facade_attr(name, default)
    return helper if callable(helper) and helper is not default else default


def _profile_create_allowed_fields() -> set[str]:
    fields = _facade_attr("PROFILE_CREATE_ALLOWED_FIELDS", PROFILE_CREATE_ALLOWED_FIELDS)
    return {str(field) for field in fields} if isinstance(fields, (set, list, tuple)) else PROFILE_CREATE_ALLOWED_FIELDS


def _profile_create_max_text_length() -> int:
    try:
        value = int(_facade_attr("PROFILE_CREATE_MAX_TEXT_LENGTH", PROFILE_CREATE_MAX_TEXT_LENGTH))
    except (TypeError, ValueError):
        return PROFILE_CREATE_MAX_TEXT_LENGTH
    return value if value > 0 else PROFILE_CREATE_MAX_TEXT_LENGTH


def _profile_create_max_binary_bytes() -> int:
    try:
        value = int(_facade_attr("PROFILE_CREATE_MAX_BINARY_BYTES", PROFILE_CREATE_MAX_BINARY_BYTES))
    except (TypeError, ValueError):
        return PROFILE_CREATE_MAX_BINARY_BYTES
    return value if value > 0 else PROFILE_CREATE_MAX_BINARY_BYTES


def _desk_delivery_target_id() -> str:
    return str(_facade_attr("DESK_DELIVERY_TARGET_ID", DESK_DELIVERY_TARGET_ID) or DESK_DELIVERY_TARGET_ID)


def _project_root() -> Path:
    return Path(_facade_attr("PROJECT_ROOT", PROJECT_ROOT))


def _utc_now() -> str:
    now_fn = _facade_attr("_utc_now", None)
    if callable(now_fn) and now_fn is not _utc_now:
        return str(now_fn())
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def create_profile_from_brief(conn, body: dict) -> dict:
    unexpected = sorted(str(key) for key in body.keys() if key not in _profile_create_allowed_fields())
    if unexpected:
        raise ValueError(f"Unsupported profile creation field: {', '.join(unexpected)}")
    brief = _facade_callable("_profile_create_input_text", _profile_create_input_text)(body)
    title = _facade_callable("_profile_title_from_text", _profile_title_from_text)(brief)
    project_root = _project_root()
    profile_id = _facade_callable("_unique_profile_id", _unique_profile_id)(
        conn,
        _facade_callable("_slugify_profile_id", _slugify_profile_id)(title),
    )
    profile_rel_path = Path("profiles") / "desk" / f"{profile_id}.md"
    profile_path = project_root / profile_rel_path
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(_facade_callable("_profile_markdown_from_brief", _profile_markdown_from_brief)(title, brief), encoding="utf-8")

    config = {
        "id": profile_id,
        "path": profile_rel_path.as_posix(),
        "enabled": True,
        "timezone": "Asia/Shanghai",
        "work_interval_minutes": 30,
        "off_hours_interval_minutes": 120,
        "scan_window_hours": 2,
        "source_registry": ".tgcs/sources.json",
        "channel_list": "channel_lists/example.txt",
        "source_topics": ["jobs"],
        "alert_rule": "high_new_or_changed",
        "alert_schedule_mode": "work_hours",
        "delivery_targets": [_desk_delivery_target_id()],
        "dashboard_visible": True,
        "prefilter_enabled": True,
        "scan_concurrency": monitor_config.DEFAULT_FAST_JOBS_SCAN_CONCURRENCY,
        "scan_delay_seconds": monitor_config.DEFAULT_FAST_JOBS_SCAN_DELAY_SECONDS,
        "semantic_max_messages": monitor_config.DEFAULT_FAST_JOBS_SEMANTIC_MAX_MESSAGES,
        "semantic_max_tokens": monitor_config.DEFAULT_FAST_JOBS_SEMANTIC_MAX_TOKENS,
        "semantic_batch_size": monitor_config.DEFAULT_FAST_JOBS_SEMANTIC_BATCH_SIZE,
        "semantic_concurrency": monitor_config.DEFAULT_FAST_JOBS_SEMANTIC_CONCURRENCY,
        "prefilter_keywords": _facade_callable("_profile_keywords_from_text", _profile_keywords_from_text)(brief),
    }
    _facade_callable("_append_profile_config", _append_profile_config)(config)
    monitor_state.upsert_profile(conn, {**config, "path": str(profile_path)})
    return {
        "schema_version": "desk_profile_create_result_v1",
        "profile_id": profile_id,
        "display_name": title,
        "profile_path": profile_rel_path.as_posix(),
        "created": True,
        "detail": "Profile created from your brief. Review its matching rules, then run a practice scan.",
        "next_action": "Open the new profile, adjust matching rules if needed, then run a practice scan from Start.",
        "created_at": _utc_now(),
    }


def delete_profile(conn, profile_id: str) -> dict:
    profile_id = str(profile_id or "").strip()
    if not profile_id:
        raise ValueError("Profile id is required.")
    row = conn.execute("SELECT * FROM profiles WHERE profile_id = ?", (profile_id,)).fetchone()
    if not row:
        raise monitor_state.MonitorStateError(f"Profile is not registered: {profile_id}")
    profile_path = Path(str(row["path"] or ""))
    removed_from_config = _remove_profile_config(profile_id)
    removed_profile_file = _remove_desk_profile_file(profile_path)
    result = monitor_state.delete_profile(conn, profile_id=profile_id)
    return {
        **result,
        "removed_from_config": removed_from_config,
        "removed_profile_file": removed_profile_file,
        "detail": "Profile deleted from Signal Desk.",
    }


def _remove_profile_config(profile_id: str) -> bool:
    path = _project_root() / ".tgcs" / "profiles.toml"
    if not path.exists():
        return False
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    blocks: list[tuple[int, int]] = []
    index = 0
    while index < len(lines):
        if lines[index].strip() != "[[profiles]]":
            index += 1
            continue
        start = index
        index += 1
        while index < len(lines) and not lines[index].lstrip().startswith("["):
            index += 1
        blocks.append((start, index))

    if not blocks:
        return False

    remove_ranges: set[tuple[int, int]] = set()
    for start, end in blocks:
        block = "".join(lines[start:end])
        if _profile_block_id(block) == profile_id:
            remove_ranges.add((start, end))

    if not remove_ranges:
        return False

    kept: list[str] = []
    for line_index, line in enumerate(lines):
        if any(start <= line_index < end for start, end in remove_ranges):
            continue
        kept.append(line)
    path.write_text("".join(kept), encoding="utf-8", newline="")
    return True


def _profile_block_id(block: str) -> str:
    for line in block.splitlines():
        match = re.match(r"\s*id\s*=\s*(['\"])(.*?)\1\s*(?:#.*)?$", line)
        if match:
            return match.group(2)
    return ""


def _remove_desk_profile_file(path_value: Path) -> bool:
    project_root = _project_root().resolve()
    profile_path = path_value if path_value.is_absolute() else project_root / path_value
    try:
        resolved = profile_path.resolve()
        resolved.relative_to(project_root / "profiles" / "desk")
    except ValueError:
        return False
    if not resolved.is_file():
        return False
    resolved.unlink()
    return True


def _profile_create_input_text(body: dict) -> str:
    parts: list[str] = []
    brief = str(body.get("brief") or "").strip()
    if brief:
        parts.append(brief)
    source_text = str(body.get("source_text") or "").strip()
    if source_text:
        parts.append(source_text)
    source_base64 = str(body.get("source_base64") or "").strip()
    if source_base64:
        filename = str(body.get("source_filename") or "").strip()
        parts.append(_facade_callable("_profile_text_from_base64_file", _profile_text_from_base64_file)(source_base64, filename))
    text = "\n\n".join(part for part in parts if part.strip()).strip()
    if not text:
        raise ValueError("Describe the profile or attach a Markdown, text, or PDF file.")
    max_text_length = _profile_create_max_text_length()
    if len(text) > max_text_length:
        raise ValueError(f"Profile brief must be {max_text_length} characters or fewer after parsing.")
    return monitor_state.require_profile_text_without_private_fragments("Profile brief", text)


def _profile_text_from_base64_file(source_base64: str, filename: str) -> str:
    raw_text = source_base64.split(",", 1)[-1]
    try:
        data = base64.b64decode(raw_text, validate=False)
    except ValueError as exc:
        raise ValueError("Could not read the attached profile file.") from exc
    if len(data) > _profile_create_max_binary_bytes():
        raise ValueError("Profile file is too large for local parsing.")
    if Path(filename).suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError("PDF parsing is not installed on this machine; use Markdown or text for now.") from exc
        text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages).strip()
        if not text:
            raise ValueError("The PDF did not contain readable text. Paste the profile brief instead.")
        return text
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="ignore")


def _profile_title_from_text(text: str) -> str:
    for raw in text.splitlines():
        line = re.sub(r"^[#>*\-\s]+", "", raw).strip()
        line = re.sub(r"\s+", " ", line)
        if line:
            return line[:72].strip(" :-") or "Custom Monitor"
    return "Custom Monitor"


def _slugify_profile_id(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug[:48].strip("-") or "custom-monitor"


def _unique_profile_id(conn, base_slug: str) -> str:
    existing = {str(row["profile_id"]) for row in conn.execute("SELECT profile_id FROM profiles").fetchall()}
    config_path = _project_root() / ".tgcs" / "profiles.toml"
    if config_path.exists():
        try:
            with config_path.open("rb") as handle:
                payload = tomllib.load(handle)
            for item in payload.get("profiles") or []:
                if isinstance(item, dict) and item.get("id"):
                    existing.add(str(item["id"]))
        except (OSError, tomllib.TOMLDecodeError):
            pass
    candidate = base_slug
    suffix = 2
    project_root = _project_root()
    while candidate in existing or (project_root / "profiles" / "desk" / f"{candidate}.md").exists():
        candidate = f"{base_slug[:42].strip('-')}-{suffix}"
        suffix += 1
    return candidate


def _profile_keywords_from_text(text: str) -> list[str]:
    seen: set[str] = set()
    keywords: list[str] = []
    for word in re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{2,}", text.lower()):
        cleaned = word.strip(".-")
        if cleaned in seen or cleaned in {"the", "and", "with", "from", "that", "this", "profile", "monitor"}:
            continue
        seen.add(cleaned)
        keywords.append(cleaned)
        if len(keywords) >= 18:
            break
    return keywords or ["hiring", "opportunity", "role", "project", "apply"]


def _profile_markdown_from_brief(title: str, brief: str) -> str:
    rules = _facade_callable("_profile_rule_lines", _profile_rule_lines)(brief)
    goal = _facade_callable("_profile_sentence", _profile_sentence)(brief)
    toml_escape = _facade_callable("_toml_escape_inline", _toml_escape_inline)
    slugify = _facade_callable("_slugify_profile_id", _slugify_profile_id)
    return "\n".join(
        [
            f"# Profile: {title}",
            "",
            "## Basic Info",
            f"- **Goal**: {goal}",
            "- **Work format**: Use the pasted brief as the user's matching preference.",
            "- **Review style**: Prefer actionable items with clear next steps; reject vague promos.",
            "",
            "## Search Rules",
            *[f"{index + 1}. {rule}" for index, rule in enumerate(rules)],
            f"{len(rules) + 1}. Rate each item as high, medium, or low based on fit, freshness, and actionability.",
            f"{len(rules) + 2}. Keep low-priority items only when they explain a useful boundary.",
            "",
            "## Extraction Schema",
            "mode: custom",
            "top_level_key: items",
            "dedup_fields: [title, source]",
            "fields:",
            "  - name: source_message_refs",
            "    type: list",
            "  - name: source_message_ids",
            "    type: list",
            "  - name: title",
            "    required: true",
            "  - name: source",
            "  - name: contact",
            "  - name: link",
            "  - name: rating",
            "    values: [high, medium, low]",
            "  - name: why",
            "  - name: action",
            "    values: [Act now, Inspect, Skip unless criteria change]",
            "",
            "## Extraction Prompt",
            "system_prompt: |",
            "  Extract only Telegram items that match this monitor profile. Keep each item",
            "  compact and actionable. Do not copy long source text; explain why the item",
            "  matters in one sentence and preserve source references.",
            "",
            "## Report Preferences",
            "- Put high-priority items first and explain the fastest safe next step.",
            "- For medium matches, state what must be verified before acting.",
            "- For low matches, state which criterion would need to change.",
            "",
            "## Follow-up Preferences",
            "- No extra learned preferences yet.",
            "",
            "## Report Labels",
            f'report_title: "{toml_escape(title)} Signal Report"',
            'section_high: "Act Now"',
            'section_medium: "Inspect First"',
            'section_low: "Boundary Examples"',
            f'stats_label: "{toml_escape(title)} matches"',
            f'output_filename: "{slugify(title)}-signal-report-{{date}}.md"',
            f'profile_section_title: "{toml_escape(title)} Profile"',
            'methodology_label: "Telegram source monitoring"',
            "",
        ]
    )


def _profile_rule_lines(text: str) -> list[str]:
    candidates: list[str] = []
    for raw in text.splitlines():
        line = re.sub(r"^[#>*\-\d.\s]+", "", raw).strip()
        line = re.sub(r"\s+", " ", line)
        if 12 <= len(line) <= 180:
            candidates.append(line.rstrip("."))
        if len(candidates) >= 5:
            break
    return candidates or ["Include items that match the user's pasted brief", "Ignore vague, low-confidence, or off-profile items"]


def _profile_sentence(text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:220].rstrip(" ,.;") or "Monitor a custom set of Telegram signals"


def _toml_escape_inline(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _toml_array(values: list[str]) -> str:
    return "[" + ", ".join(_toml_string(value) for value in values) + "]"


def _append_profile_config(config: dict) -> None:
    path = _project_root() / ".tgcs" / "profiles.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(
            "\n".join(
                [
                    'schema_version = "profile_run_config_v1"',
                    "",
                    "[defaults]",
                    'output_dir = "output"',
                    'state_dir = ".tgcs/state"',
                    'database = ".tgcs/tgcs.db"',
                    'dashboard_url = "http://127.0.0.1:8765"',
                    "",
                ]
            ),
            encoding="utf-8",
        )
    block = [
        "",
        "[[profiles]]",
        f'id = {_toml_string(config["id"])}',
        f'path = {_toml_string(config["path"])}',
        "enabled = true",
        f'timezone = {_toml_string(config["timezone"])}',
        f'work_interval_minutes = {config["work_interval_minutes"]}',
        f'off_hours_interval_minutes = {config["off_hours_interval_minutes"]}',
        f'scan_window_hours = {config["scan_window_hours"]}',
        f'source_registry = {_toml_string(config["source_registry"])}',
        f'channel_list = {_toml_string(config["channel_list"])}',
        f'source_topics = {_toml_array(config["source_topics"])}',
        f'alert_rule = {_toml_string(config["alert_rule"])}',
        f'alert_schedule_mode = {_toml_string(config["alert_schedule_mode"])}',
        f'delivery_targets = {_toml_array(config["delivery_targets"])}',
        "dashboard_visible = true",
        "prefilter_enabled = true",
        f'scan_concurrency = {config["scan_concurrency"]}',
        f'scan_delay_seconds = {config["scan_delay_seconds"]}',
        f'semantic_max_messages = {config["semantic_max_messages"]}',
        f'semantic_max_tokens = {config["semantic_max_tokens"]}',
        f'semantic_batch_size = {config["semantic_batch_size"]}',
        f'semantic_concurrency = {config["semantic_concurrency"]}',
        f'prefilter_keywords = {_toml_array(config["prefilter_keywords"])}',
        "",
    ]
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(block))
