"""Source registry, source access, and source assistant helpers for Signal Desk."""

from __future__ import annotations

import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts import desk_scheduler, desk_source_access, desk_source_assistant, source_registry


def _positive_int_env(name: str, fallback: int) -> int:
    try:
        parsed = int(os.environ.get(name, ""))
    except ValueError:
        return fallback
    return parsed if parsed > 0 else fallback


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TELEGRAM_SESSION_PATH = Path(
    os.environ.get("TG_SCANNER_CONFIG_DIR")
    or os.environ.get("TGCLI_CONFIG_DIR")
    or os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), ".config", "tgcli")
) / "session"
DESK_SOURCE_ACCESS_HEALTH_SCHEMA_VERSION = desk_source_access.DESK_SOURCE_ACCESS_HEALTH_SCHEMA_VERSION
DESK_SOURCE_ACCESS_PROBE_MAX_SOURCES = _positive_int_env(
    "TGCS_SOURCE_ACCESS_PROBE_MAX_SOURCES",
    desk_source_access.DESK_SOURCE_ACCESS_PROBE_MAX_SOURCES,
)
DESK_SOURCE_ACCESS_HEALTH_MAX_AGE_HOURS = desk_source_access.DESK_SOURCE_ACCESS_HEALTH_MAX_AGE_HOURS
DESK_SOURCE_IMPORT_ALLOWED_FIELDS = {"sources", "topic"}
DESK_SOURCE_STARTER_ALLOWED_FIELDS = {"topic"}
DESK_SOURCE_ASSISTANT_ALLOWED_FIELDS = desk_source_assistant.DESK_SOURCE_ASSISTANT_ALLOWED_FIELDS
DESK_SOURCE_UPDATE_ALLOWED_FIELDS = {"enabled"}
DESK_SOURCE_TOPIC_ALLOWED_FIELDS = {"topics"}
DESK_SOURCE_IMPORT_MAX_TEXT_LENGTH = 20000
DESK_SOURCE_IMPORT_MAX_CHANNELS = 500
DashboardDeskActionError = desk_scheduler.DashboardDeskActionError
SourceAccessProbeError = desk_source_access.SourceAccessProbeError


def _facade_attr(name: str, default: Any) -> Any:
    facade = sys.modules.get("scripts.dashboard_server")
    return getattr(facade, name, default) if facade is not None else default


def _project_root() -> Path:
    return Path(_facade_attr("PROJECT_ROOT", PROJECT_ROOT))


def _telegram_session_path() -> Path:
    return Path(_facade_attr("TELEGRAM_SESSION_PATH", TELEGRAM_SESSION_PATH))


def _utc_now() -> str:
    now_fn = _facade_attr("_utc_now", None)
    if callable(now_fn) and now_fn is not _utc_now:
        return str(now_fn())
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _dashboard_relative_path(path: Path) -> str:
    helper = _facade_attr("dashboard_relative_path", None)
    if callable(helper):
        return str(helper(path))
    try:
        return str(path.resolve().relative_to(_project_root().resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _desk_action_result(*args: Any, **kwargs: Any) -> dict:
    helper = _facade_attr("_desk_action_result", None)
    if callable(helper) and helper is not _desk_action_result:
        return helper(*args, **kwargs)
    raise DashboardDeskActionError("Desk action result projection is unavailable.")


def _load_telegram_credentials(*args: Any, **kwargs: Any) -> tuple[int, str]:
    helper = _facade_attr("_load_telegram_credentials", None)
    if not callable(helper):
        raise ValueError("Telegram app credentials are missing.")
    return helper(*args, **kwargs)

def _reject_unexpected_source_fields(body: dict) -> None:
    unexpected = sorted(str(key) for key in body.keys() if key not in DESK_SOURCE_IMPORT_ALLOWED_FIELDS)
    if unexpected:
        raise ValueError(f"Unsupported source import field: {', '.join(unexpected)}")


def _reject_unexpected_source_starter_fields(body: dict) -> None:
    unexpected = sorted(str(key) for key in body.keys() if key not in DESK_SOURCE_STARTER_ALLOWED_FIELDS)
    if unexpected:
        raise ValueError(f"Unsupported starter source field: {', '.join(unexpected)}")


def _reject_unexpected_source_assistant_fields(body: dict) -> None:
    desk_source_assistant._reject_unexpected_source_assistant_fields(body)


def _clean_source_topic(value: object) -> str:
    topic = str(value or "jobs").strip().casefold()
    if not topic:
        topic = "jobs"
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,40}", topic):
        raise ValueError("Source topic must use letters, numbers, hyphen, or underscore.")
    return topic


def _source_import_payload(result: dict, *, topic: str, written: bool) -> dict:
    def source_label(source: dict) -> str:
        return str(source.get("username") or source.get("channel_id") or source.get("label") or "").strip()

    raw_preview_sources = [
        source
        for collection in (result.get("sources"), result.get("updated_sources"), result.get("unchanged_sources"))
        for source in (collection or [])
        if isinstance(source, dict)
    ]
    preview_sources = [
        {"label": source_label(source), "source_id": str(source.get("source_id") or "")}
        for source in raw_preview_sources[:12]
    ]
    preview_truncated_count = max(0, len(raw_preview_sources) - len(preview_sources))
    return {
        "schema_version": "desk_source_import_result_v1",
        "dry_run": bool(result.get("dry_run")),
        "written": written,
        "topic": topic,
        "added_count": int(result.get("added_count") or 0),
        "updated_count": int(result.get("updated_count") or 0),
        "unchanged_count": int(result.get("unchanged_count") or 0),
        "source_count": int(result.get("source_count") or 0),
        "registry_path": _dashboard_relative_path(Path(str(result.get("registry_path") or ".tgcs/sources.json"))),
        "preview_sources": preview_sources,
        "preview_truncated_count": preview_truncated_count,
        "title": "Sources ready" if written else "Source preview ready",
        "detail": (
            "Sources were saved to the local registry."
            if written
            else "Review the preview, then import when it looks right."
        ),
        "next_action": "Run source checks, then run a scan from Start.",
        "finished_at": _utc_now(),
    }


def _source_operation_payload(
    *,
    action: str,
    topic: str,
    dry_run: bool,
    added_count: int = 0,
    updated_count: int = 0,
    unchanged_count: int = 0,
    removed_count: int = 0,
    enabled_count: int = 0,
    disabled_count: int = 0,
    preview_sources: list[dict] | None = None,
    resolved_plan: dict[str, list[str]] | None = None,
    title: str,
    detail: str,
    llm_used: bool = False,
) -> dict:
    return {
        "schema_version": "desk_source_import_result_v1",
        "dry_run": dry_run,
        "written": not dry_run,
        "action": action,
        "topic": topic,
        "added_count": added_count,
        "updated_count": updated_count,
        "unchanged_count": unchanged_count,
        "removed_count": removed_count,
        "enabled_count": enabled_count,
        "disabled_count": disabled_count,
        "source_count": desk_sources()["source_count"],
        "registry_path": ".tgcs/sources.json",
        "preview_sources": preview_sources or [],
        "preview_truncated_count": 0,
        "resolved_plan": resolved_plan or {"add": [], "remove": [], "disable": [], "enable": []},
        "llm_used": llm_used,
        "title": title,
        "detail": detail,
        "next_action": "Run source checks, then run a scan from Start.",
        "finished_at": _utc_now(),
    }


def _desk_source_record(source: dict) -> dict:
    channel = source_registry.channel_value(source)
    label = str(source.get("label") or channel or source.get("source_id") or "").strip()
    return {
        "schema_version": "desk_source_v1",
        "source_id": str(source.get("source_id") or ""),
        "label": label,
        "channel": channel,
        "enabled": bool(source.get("enabled", True)),
        "topics": source_registry.normalize_topics(source.get("topics") or []),
        "priority": str(source.get("priority") or "normal"),
        "scan_window_hours": int(source.get("scan_window_hours") or source_registry.DEFAULT_SCAN_WINDOW_HOURS),
    }


def desk_sources() -> dict:
    registry_path = _project_root() / ".tgcs" / "sources.json"
    result = source_registry.registry_sources(registry_path)
    return {
        "schema_version": "desk_sources_v1",
        "source_count": int(result.get("source_count") or 0),
        "enabled_count": int(result.get("enabled_count") or 0),
        "topics": [str(topic) for topic in result.get("topics") or []],
        "registry_path": _dashboard_relative_path(Path(str(result.get("registry_path") or registry_path))),
        "sources": [_desk_source_record(source) for source in (result.get("sources") or []) if isinstance(source, dict)],
    }


def _validate_desk_source_id(source_id: str) -> str:
    clean = str(source_id or "").strip()
    if not re.fullmatch(r"telegram:(?:[A-Za-z0-9_]{5,64}|-?[0-9]{5,20})", clean):
        raise ValueError("Source id is not supported by Signal Desk.")
    return clean


def set_desk_source_enabled(source_id: str, body: dict) -> dict:
    unexpected = sorted(str(key) for key in body.keys() if key not in DESK_SOURCE_UPDATE_ALLOWED_FIELDS)
    if unexpected:
        raise ValueError(f"Unsupported source setting field: {', '.join(unexpected)}")
    enabled = body.get("enabled")
    if not isinstance(enabled, bool):
        raise ValueError("Source enabled value must be true or false.")
    registry_path = _project_root() / ".tgcs" / "sources.json"
    source_registry.update_source_enabled(
        registry_path,
        source_id=_validate_desk_source_id(source_id),
        enabled=enabled,
    )
    return desk_sources()


def _clean_source_topics(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("Source topics must be a list.")
    if len(value) > 8:
        raise ValueError("Use fewer topic tags.")
    topics: list[str] = []
    seen: set[str] = set()
    for raw_topic in value:
        if not isinstance(raw_topic, str):
            raise ValueError("Source topic tags must be text.")
        topic = raw_topic.strip().casefold()
        if not topic:
            continue
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,40}", topic):
            raise ValueError("Source topic must use letters, numbers, hyphen, or underscore.")
        if topic in seen:
            continue
        seen.add(topic)
        topics.append(topic)
    if not topics:
        raise ValueError("Add at least one source topic.")
    return topics


def set_desk_source_topics(source_id: str, body: dict) -> dict:
    unexpected = sorted(str(key) for key in body.keys() if key not in DESK_SOURCE_TOPIC_ALLOWED_FIELDS)
    if unexpected:
        raise ValueError(f"Unsupported source topic field: {', '.join(unexpected)}")
    topics = _clean_source_topics(body.get("topics"))
    registry_path = _project_root() / ".tgcs" / "sources.json"
    source_registry.update_source_topics(
        registry_path,
        source_id=_validate_desk_source_id(source_id),
        topics=topics,
    )
    return desk_sources()


def remove_desk_source(source_id: str, body: dict) -> dict:
    unexpected = sorted(str(key) for key in body.keys() if key not in {"confirm"})
    if unexpected:
        raise ValueError(f"Unsupported source remove field: {', '.join(unexpected)}")
    if body.get("confirm") is not True:
        raise ValueError("Source removal requires confirmation.")
    registry_path = _project_root() / ".tgcs" / "sources.json"
    source_registry.remove_sources(registry_path, source_ids=[_validate_desk_source_id(source_id)])
    return desk_sources()


def source_access_health_path() -> Path:
    return desk_source_access.source_access_health_path(_project_root())


def _source_access_health_loaded() -> dict | None:
    return desk_source_access._source_access_health_loaded(source_access_health_path())


def _write_source_access_health(payload: dict) -> None:
    desk_source_access._write_source_access_health(payload, source_access_health_path())


def _source_access_checked_at(payload: dict) -> datetime | None:
    return desk_source_access._source_access_checked_at(payload)


def _source_access_health_is_fresh(payload: dict, *, max_age_hours: int = DESK_SOURCE_ACCESS_HEALTH_MAX_AGE_HOURS) -> bool:
    return desk_source_access._source_access_health_is_fresh(payload, max_age_hours=max_age_hours)


def _source_access_reason_label(reason: str) -> str:
    return desk_source_access._source_access_reason_label(reason)


def _source_access_health_detail(payload: dict) -> str:
    return desk_source_access._source_access_health_detail(payload)


def _source_access_action_summary(payload: dict) -> dict:
    return desk_source_access._source_access_action_summary(payload)


def _source_access_record_base(source: dict) -> dict:
    return desk_source_access._source_access_record_base(source)


def _source_access_error_reason(exc: Exception) -> str:
    return desk_source_access._source_access_error_reason(exc)


def _source_access_failure_record(source: dict, exc: Exception) -> dict:
    return desk_source_access._source_access_failure_record(source, exc)


async def _resolve_probe_entity(client, channel: str):
    return await desk_source_access._resolve_probe_entity(client, channel)


def _message_datetime(value: object) -> datetime | None:
    return desk_source_access._message_datetime(value)


async def _probe_one_source_access(client, source: dict, *, now: datetime) -> dict:
    return await desk_source_access._probe_one_source_access(client, source, now=now)


def _source_access_summary(records: list[dict], *, total_source_count: int, truncated_count: int, checked_at: str) -> dict:
    return desk_source_access._source_access_summary(
        records,
        total_source_count=total_source_count,
        truncated_count=truncated_count,
        checked_at=checked_at,
    )


async def _probe_source_access_async(progress_callback=None) -> dict:
    summary = await desk_source_access._probe_source_access_async(
        registry_path=_project_root() / ".tgcs" / "sources.json",
        telegram_session_path=_telegram_session_path(),
        load_telegram_credentials=_load_telegram_credentials,
        max_sources=DESK_SOURCE_ACCESS_PROBE_MAX_SOURCES,
        progress_callback=progress_callback,
    )
    _write_source_access_health(summary)
    return summary


def probe_source_access(progress_callback=None) -> dict:
    return desk_source_access.probe_source_access(
        registry_path=_project_root() / ".tgcs" / "sources.json",
        health_path=source_access_health_path(),
        telegram_session_path=_telegram_session_path(),
        load_telegram_credentials=_load_telegram_credentials,
        max_sources=DESK_SOURCE_ACCESS_PROBE_MAX_SOURCES,
        progress_callback=progress_callback,
    )


def _require_confirm_only(body: dict | None, *, action_label: str) -> None:
    desk_source_access._require_confirm_only(body, action_label=action_label)


def _source_access_target_ids(payload: dict, *, keep_only_accessible: bool) -> list[str]:
    return desk_source_access._source_access_target_ids(
        payload,
        keep_only_accessible=keep_only_accessible,
        validate_source_id=_validate_desk_source_id,
    )


def _disable_sources_from_access_health(source_ids: list[str]) -> int:
    return desk_source_access._disable_sources_from_access_health(
        source_ids,
        registry_path=_project_root() / ".tgcs" / "sources.json",
    )


def apply_source_access_repair(action_id: str, *, body: dict | None = None) -> dict:
    return desk_source_access.apply_source_access_repair(
        action_id,
        body=body,
        health_path=source_access_health_path(),
        registry_path=_project_root() / ".tgcs" / "sources.json",
        desk_action_result=_desk_action_result,
        validate_source_id=_validate_desk_source_id,
    )


def _desk_sources_from_body(body: dict) -> tuple[list[str], str]:
    _reject_unexpected_source_fields(body)
    text = str(body.get("sources") or "")
    if len(text) > DESK_SOURCE_IMPORT_MAX_TEXT_LENGTH:
        raise ValueError("Paste fewer sources at a time.")
    channels = source_registry.load_channel_text(text)
    if not channels:
        raise ValueError("Paste at least one Telegram channel handle or t.me link.")
    if len(channels) > DESK_SOURCE_IMPORT_MAX_CHANNELS:
        raise ValueError("Paste fewer sources at a time.")
    invalid_channels = [
        channel
        for channel in channels
        if not re.fullmatch(r"(?:[A-Za-z0-9_]{5,64}|-?[0-9]{5,20})", channel)
    ]
    if invalid_channels:
        raise ValueError("Source import only accepts Telegram channel handles or numeric chat IDs.")
    topic = _clean_source_topic(body.get("topic"))
    return channels, topic


def import_starter_sources(body: dict) -> dict:
    _reject_unexpected_source_starter_fields(body)
    topic = _clean_source_topic(body.get("topic"))
    starter_path = _project_root() / "channel_lists" / "jobs.txt"
    if not starter_path.exists():
        starter_path = _project_root() / "channel_lists" / "example.txt"
    if not starter_path.exists():
        raise ValueError("Starter source list is missing from this checkout.")
    channels = source_registry.load_channel_list(starter_path)
    registry_path = _project_root() / ".tgcs" / "sources.json"
    result = source_registry.import_channels(
        channels,
        registry_path,
        dry_run=False,
        topics=[topic],
        input_path="packaged starter sources",
    )
    payload = _source_import_payload(result, topic=topic, written=True)
    payload["title"] = "Starter sources installed"
    payload["detail"] = "Signal Desk added the packaged starter source set. Replace or prune it from Settings as you learn what works."
    return payload


def preview_desk_source_import(body: dict) -> dict:
    channels, topic = _desk_sources_from_body(body)
    registry_path = _project_root() / ".tgcs" / "sources.json"
    result = source_registry.import_channels(
        channels,
        registry_path,
        dry_run=True,
        topics=[topic],
        input_path="pasted sources",
    )
    return _source_import_payload(result, topic=topic, written=False)


def import_desk_sources(body: dict) -> dict:
    channels, topic = _desk_sources_from_body(body)
    registry_path = _project_root() / ".tgcs" / "sources.json"
    result = source_registry.import_channels(
        channels,
        registry_path,
        dry_run=False,
        topics=[topic],
        input_path="pasted sources",
    )
    return _source_import_payload(result, topic=topic, written=True)


def _extract_source_channels_from_text(text: str) -> list[str]:
    return desk_source_assistant._extract_source_channels_from_text(text)


def _source_id_from_channel(channel: str) -> str:
    return desk_source_assistant._source_id_from_channel(channel)


def _source_assistant_action(text: str) -> str:
    return desk_source_assistant._source_assistant_action(text)


def _source_assistant_plan(instruction: str) -> dict[str, list[str]]:
    return desk_source_assistant._source_assistant_plan(instruction)


def _source_assistant_has_plan(plan: dict[str, list[str]]) -> bool:
    return desk_source_assistant._source_assistant_has_plan(plan)


def _source_assistant_requested_existing_actions(instruction: str) -> set[str]:
    return desk_source_assistant._source_assistant_requested_existing_actions(instruction)


def _source_assistant_should_use_llm_plan(instruction: str, plan: dict[str, list[str]]) -> bool:
    return desk_source_assistant._source_assistant_should_use_llm_plan(instruction, plan)


def _dedupe_source_ids(source_ids: list[str]) -> list[str]:
    return desk_source_assistant._dedupe_source_ids(source_ids, validate_source_id=_validate_desk_source_id)


def _dedupe_source_channels(channels: list[str]) -> list[str]:
    return desk_source_assistant._dedupe_source_channels(channels)


def _clean_resolved_source_plan(plan: dict) -> dict[str, list[str]]:
    return desk_source_assistant._clean_resolved_source_plan(plan, validate_source_id=_validate_desk_source_id)


def _source_assistant_llm_plan(instruction: str, topic: str, existing: dict[str, dict]) -> dict[str, list[str]]:
    return desk_source_assistant._source_assistant_llm_plan(
        instruction,
        topic,
        existing,
        validate_source_id=_validate_desk_source_id,
    )


def run_source_assistant(body: dict) -> dict:
    return desk_source_assistant.run_source_assistant(
        body,
        registry_path=_project_root() / ".tgcs" / "sources.json",
        clean_source_topic=_clean_source_topic,
        source_operation_payload=_source_operation_payload,
        desk_source_record=_desk_source_record,
        validate_source_id=_validate_desk_source_id,
        llm_plan_fn=_facade_attr("_source_assistant_llm_plan", _source_assistant_llm_plan),
    )


def apply_source_assistant_resolved_plan(plan: dict, topic: str) -> dict:
    return desk_source_assistant.apply_source_assistant_resolved_plan(
        plan,
        topic,
        registry_path=_project_root() / ".tgcs" / "sources.json",
        clean_source_topic=_clean_source_topic,
        source_operation_payload=_source_operation_payload,
        desk_source_record=_desk_source_record,
        validate_source_id=_validate_desk_source_id,
    )
