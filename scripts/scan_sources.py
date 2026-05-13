"""Source loading and source-level scan health helpers."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

try:
    from scripts import source_registry
    from scripts.scan_config import DEFAULT_HOURS, ScanError
except ModuleNotFoundError:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts import source_registry
    from scripts.scan_config import DEFAULT_HOURS, ScanError



@dataclass
class ChannelResult:
    channel: str
    messages: list[dict]
    raw_count: int
    skipped_missing_date: int
    limit: int
    incomplete: bool
    ocr_count: int = 0
    stderr: str = ""



@dataclass
class ScanSource:
    channel: str
    source_id: str | None = None
    username: str | None = None
    channel_id: int | None = None
    label: str | None = None
    topics: list[str] | None = None
    priority: str | None = None
    expected_language: str | None = None
    scan_window_hours: int | None = None



def load_channel_list(path: Path) -> list[str]:
    channels: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            channels.append(line)
    return channels



def source_from_channel_list_entry(channel: str) -> ScanSource:
    original = str(channel or "").strip()
    normalized = source_registry.normalize_channel_name(original)
    username = normalized if not normalized.lstrip("-").isdigit() else None
    channel_id = int(normalized) if normalized.lstrip("-").isdigit() else None
    return ScanSource(
        channel=original,
        source_id=source_registry.source_id_for(username, channel_id),
        username=username,
        channel_id=channel_id,
        label=original,
        topics=[],
        priority="normal",
        expected_language="",
        scan_window_hours=None,
    )



def source_from_registry_entry(entry: dict) -> ScanSource:
    channel = source_registry.channel_value(entry)
    return ScanSource(
        channel=channel,
        source_id=entry.get("source_id"),
        username=entry.get("username"),
        channel_id=entry.get("channel_id"),
        label=entry.get("label") or channel,
        topics=list(entry.get("topics") or []),
        priority=entry.get("priority"),
        expected_language=entry.get("expected_language"),
        scan_window_hours=entry.get("scan_window_hours"),
    )



def load_scan_sources(args) -> tuple[list[ScanSource], dict | None]:
    if args.source_registry:
        payload = source_registry.load_registry(args.source_registry)
        issues = source_registry.validate_registry(payload)
        if issues:
            raise ScanError(source_registry.validation_message(issues))
        return [
            source_from_registry_entry(entry)
            for entry in source_registry.enabled_sources(payload)
            if source_registry.channel_value(entry)
        ], payload
    if not args.channel_list:
        raise ScanError("Missing source input. Pass a channel list or --source-registry.")
    channels = load_channel_list(args.channel_list)
    return [source_from_channel_list_entry(channel) for channel in channels], None



def scan_hours(args) -> int:
    return args.hours_flag or args.hours or DEFAULT_HOURS



def parse_message_date(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)



def filter_messages(
    messages: Iterable[dict], cutoff: datetime
) -> tuple[list[dict], int]:
    kept: list[dict] = []
    skipped_missing_date = 0
    cutoff_utc = cutoff.astimezone(UTC)
    for message in messages:
        message_date = parse_message_date(message.get("date"))
        if message_date is None:
            skipped_missing_date += 1
            continue
        if message_date >= cutoff_utc:
            kept.append(message)
    return kept, skipped_missing_date



def _filter_raw_messages(
    messages: list, cutoff: datetime
) -> tuple[list, int]:
    """Filter Telethon Message objects by cutoff."""
    cutoff_utc = cutoff.astimezone(UTC)
    kept: list = []
    skipped = 0
    for m in messages:
        if m.date is None:
            skipped += 1
            continue
        d = m.date if m.date.tzinfo else m.date.replace(tzinfo=UTC)
        if d.astimezone(UTC) >= cutoff_utc:
            kept.append(m)
    return kept, skipped



def write_jsonl(path: Path, messages: Iterable[dict]) -> int:
    count = 0
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for message in messages:
            handle.write(json.dumps(message, ensure_ascii=False))
            handle.write("\n")
            count += 1
    return count



def _source_health_base(source: ScanSource) -> dict:
    return {
        "source_id": source.source_id,
        "channel": source.channel,
        "username": source.username,
        "channel_id": source.channel_id,
        "label": source.label,
        "topics": source.topics or [],
        "priority": source.priority,
        "expected_language": source.expected_language,
        "scan_window_hours": source.scan_window_hours,
        "raw_count": 0,
        "kept_count": 0,
        "oldest_message_at": None,
        "newest_message_at": None,
        "incomplete": False,
        "failure": None,
        "last_error": None,
        "ocr_count": 0,
    }



def source_access_failure_reason(exc: Exception) -> str:
    name = exc.__class__.__name__.casefold()
    text = str(exc).casefold()
    if "floodwait" in name or "flood wait" in text or "too many requests" in text:
        return "rate_limited"
    if "timeout" in name or "timed out" in text or "timeout" in text:
        return "timeout"
    if any(marker in text for marker in ("cannot resolve", "cannot resolve channel", "cannot resolve entity", "could not find the input entity", "no user has")):
        return "cannot_resolve_entity"
    if any(marker in text for marker in ("private", "forbidden", "not a participant", "invite", "permission")):
        return "permission_or_private"
    return "access_error"



def _health_from_result(source: ScanSource, result: ChannelResult, kept_count: int) -> dict:
    health = _source_health_base(source)
    message_dates = [
        parsed
        for parsed in (parse_message_date(message.get("date")) for message in result.messages)
        if parsed is not None
    ]
    health.update(
        {
            "channel": result.channel,
            "raw_count": result.raw_count,
            "kept_count": kept_count,
            "oldest_message_at": min(message_dates).isoformat() if message_dates else None,
            "newest_message_at": max(message_dates).isoformat() if message_dates else None,
            "incomplete": result.incomplete,
            "ocr_count": result.ocr_count,
        }
    )
    return health



def _health_from_failure(source: ScanSource, exc: Exception) -> dict:
    health = _source_health_base(source)
    health.update({
        "failure": type(exc).__name__,
        "failure_reason": source_access_failure_reason(exc),
        "last_error": str(exc),
    })
    return health
