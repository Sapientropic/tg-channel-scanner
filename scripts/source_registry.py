"""Private source registry operations for T-Sense.

The registry is intentionally a small JSON file. It gives agents a stable
source-of-truth for local operations without forcing users to migrate away from
plain channel list files.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

try:
    from scripts import agent_cli
except ModuleNotFoundError:
    _PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    from scripts import agent_cli


SCHEMA_VERSION = "source_registry_v1"
VALID_PRIORITIES = {"low", "normal", "high"}
DEFAULT_SCAN_WINDOW_HOURS = 24
DEFAULT_REGISTRY_RELATIVE_PATH = Path(".tgcs") / "sources.json"
_TME_URL_RE = re.compile(r"^(?:https?://)?t\.me/(?:s/)?([^/?#]+)", re.IGNORECASE)
_SOURCE_ID_RE = re.compile(r"^telegram:(?:[A-Za-z0-9_]{5,64}|-?[0-9]{5,20})$")
_TOPIC_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,40}$")
MAX_TOPICS = 8


class RegistryError(Exception):
    pass


def default_registry_path() -> Path:
    configured = os.environ.get("TGCS_SOURCE_REGISTRY")
    return Path(configured) if configured else DEFAULT_REGISTRY_RELATIVE_PATH


def normalize_channel_name(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    match = _TME_URL_RE.match(text)
    if match:
        text = match.group(1)
    return text.strip().lstrip("@")


def load_channel_list(path: Path) -> list[str]:
    channels: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            line = normalize_channel_name(raw)
            if not line or line.startswith("#"):
                continue
            channels.append(line)
    return channels


def load_channel_text(text: str) -> list[str]:
    channels: list[str] = []
    for raw in text.splitlines():
        line = normalize_channel_name(raw)
        if not line or line.startswith("#"):
            continue
        channels.append(line)
    return channels


def source_id_for(username: str | None, channel_id: int | str | None) -> str:
    if username:
        return f"telegram:{normalize_channel_name(username).casefold()}"
    if channel_id not in (None, ""):
        return f"telegram:{channel_id}"
    raise RegistryError("source must include username or channel_id")


def source_from_channel(value: str) -> dict:
    channel = normalize_channel_name(value)
    if not channel:
        raise RegistryError("channel name cannot be empty")
    username: str | None = channel
    channel_id: int | None = None
    if channel.lstrip("-").isdigit():
        username = None
        channel_id = int(channel)
    label = username or str(channel_id)
    return {
        "source_id": source_id_for(username, channel_id),
        "username": username,
        "channel_id": channel_id,
        "label": label,
        "topics": [],
        "priority": "normal",
        "expected_language": "",
        "scan_window_hours": DEFAULT_SCAN_WINDOW_HOURS,
        "enabled": True,
        "notes": "",
    }


def _source_metadata_for(channel: str, source_metadata: dict[str, dict[str, Any]] | None) -> dict[str, Any]:
    if not source_metadata:
        return {}
    return source_metadata.get(normalize_channel_name(channel).casefold(), {})


def apply_source_metadata(source: dict, metadata: dict[str, Any]) -> bool:
    if not isinstance(metadata, dict):
        return False
    changed = False
    for field in ("label", "expected_language", "notes"):
        value = str(metadata.get(field) or "").strip()
        if not value or source.get(field) == value:
            continue
        source[field] = value
        changed = True
    return changed


def normalize_topics(values: list[str] | None) -> list[str]:
    topics: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        if not isinstance(value, str):
            raise RegistryError("Topic tags must be strings")
        topic = value.strip().casefold()
        if not topic or topic in seen:
            continue
        if not _TOPIC_RE.fullmatch(topic):
            raise RegistryError(f"Invalid topic tag: {topic}")
        seen.add(topic)
        topics.append(topic)
        if len(topics) > MAX_TOPICS:
            raise RegistryError(f"Use no more than {MAX_TOPICS} topic tags")
    return topics


def load_registry(path: Path | None = None, *, missing_ok: bool = False) -> dict:
    registry_path = path or default_registry_path()
    if not registry_path.exists():
        if missing_ok:
            return {"schema_version": SCHEMA_VERSION, "sources": []}
        raise RegistryError(f"Source registry not found: {registry_path}")
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RegistryError(f"Source registry is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise RegistryError("Source registry root must be an object.")
    return payload


def save_registry(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temp_path.open("w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def validate_registry(payload: dict) -> list[str]:
    issues: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        issues.append(f"schema_version must be {SCHEMA_VERSION}")
    sources = payload.get("sources")
    if not isinstance(sources, list):
        issues.append("sources must be a list")
        return issues

    seen: set[str] = set()
    duplicates: set[str] = set()
    for index, source in enumerate(sources):
        prefix = f"sources[{index}]"
        if not isinstance(source, dict):
            issues.append(f"{prefix} must be an object")
            continue
        source_id = source.get("source_id")
        username = source.get("username")
        channel_id = source.get("channel_id")
        if not isinstance(source_id, str) or not source_id.strip():
            issues.append(f"{prefix}.source_id is required")
        elif not _SOURCE_ID_RE.fullmatch(source_id.strip()):
            issues.append(f"{prefix}.source_id must be a Telegram source id")
        elif source_id in seen:
            duplicates.add(source_id)
        else:
            seen.add(source_id)
        if not username and channel_id in (None, ""):
            issues.append(f"{prefix} must include username or channel_id")
        if username is not None and not isinstance(username, str):
            issues.append(f"{prefix}.username must be a string or null")
        if channel_id not in (None, "") and not isinstance(channel_id, int):
            issues.append(f"{prefix}.channel_id must be an integer or null")
        if source.get("priority") not in VALID_PRIORITIES:
            issues.append(f"{prefix}.priority must be one of {sorted(VALID_PRIORITIES)}")
        topics_value = source.get("topics", [])
        if not isinstance(topics_value, list):
            issues.append(f"{prefix}.topics must be a list")
        else:
            try:
                normalize_topics(topics_value)
            except RegistryError as exc:
                issues.append(f"{prefix}.topics {exc}")
        if not isinstance(source.get("expected_language", ""), str):
            issues.append(f"{prefix}.expected_language must be a string")
        window = source.get("scan_window_hours")
        if not isinstance(window, int) or window <= 0:
            issues.append(f"{prefix}.scan_window_hours must be a positive integer")
        if not isinstance(source.get("enabled", True), bool):
            issues.append(f"{prefix}.enabled must be a boolean")
    for source_id in sorted(duplicates):
        issues.append(f"duplicate source_id: {source_id}")
    return issues


def validation_message(issues: list[str]) -> str:
    duplicate = next((issue for issue in issues if issue.startswith("duplicate source_id")), None)
    if duplicate:
        return f"Source registry is invalid: {duplicate}"
    return "Source registry is invalid."


def enabled_sources(payload: dict) -> list[dict]:
    return [source for source in payload.get("sources", []) if source.get("enabled", True)]


def sources_matching_topics(sources: list[dict], topics: list[str] | None = None) -> list[dict]:
    normalized_topics = set(normalize_topics(topics))
    if not normalized_topics:
        return sources
    return [
        source
        for source in sources
        if normalized_topics.intersection(normalize_topics(source.get("topics") or []))
    ]


def channel_value(source: dict) -> str:
    username = normalize_channel_name(source.get("username"))
    if username:
        return username
    channel_id = source.get("channel_id")
    return str(channel_id) if channel_id not in (None, "") else ""


def source_lookup_by_channel(payload: dict | None) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    if not payload:
        return lookup
    for source in payload.get("sources", []):
        channel = channel_value(source)
        if channel:
            lookup[channel] = source
            lookup[channel.casefold()] = source
    return lookup


def merge_source_topics(source: dict, topics: list[str]) -> bool:
    if not topics:
        return False
    existing = normalize_topics(source.get("topics") or [])
    merged = list(existing)
    changed = False
    for topic in topics:
        if topic not in existing:
            merged.append(topic)
            existing.append(topic)
            changed = True
    if changed:
        source["topics"] = merged
    return changed


def import_channel_list(
    path: Path,
    registry_path: Path,
    *,
    dry_run: bool = False,
    topics: list[str] | None = None,
) -> dict:
    channels = load_channel_list(path)
    return import_channels(
        channels,
        registry_path,
        dry_run=dry_run,
        topics=topics,
        input_path=str(path),
    )


def import_channels(
    channels: list[str],
    registry_path: Path,
    *,
    dry_run: bool = False,
    topics: list[str] | None = None,
    input_path: str = "pasted sources",
    source_metadata: dict[str, dict[str, Any]] | None = None,
) -> dict:
    normalized_topics = normalize_topics(topics)
    payload = load_registry(registry_path, missing_ok=True)
    existing = {
        source.get("source_id"): source
        for source in payload.get("sources", [])
        if isinstance(source, dict)
    }
    added: list[dict] = []
    updated: list[dict] = []
    unchanged: list[dict] = []
    for channel in channels:
        source = source_from_channel(channel)
        metadata = _source_metadata_for(channel, source_metadata)
        apply_source_metadata(source, metadata)
        if normalized_topics:
            source["topics"] = list(normalized_topics)
        existing_source = existing.get(source["source_id"])
        if existing_source:
            metadata_changed = apply_source_metadata(existing_source, metadata)
            if merge_source_topics(existing_source, normalized_topics) or metadata_changed:
                updated.append(existing_source)
            else:
                unchanged.append(existing_source)
            continue
        payload.setdefault("sources", []).append(source)
        existing[source["source_id"]] = source
        added.append(source)
    issues = validate_registry(payload)
    if issues:
        raise RegistryError(validation_message(issues))
    if not dry_run:
        save_registry(registry_path, payload)
    return {
        "dry_run": dry_run,
        "registry_path": str(registry_path),
        "input_path": input_path,
        "added_count": len(added),
        "updated_count": len(updated),
        "unchanged_count": len(unchanged),
        "source_count": len(payload.get("sources", [])),
        "topics": normalized_topics,
        "sources": added,
        "updated_sources": updated,
        "unchanged_sources": unchanged,
    }


def export_channel_list(registry_path: Path, output: Path, *, topics: list[str] | None = None) -> dict:
    payload = load_registry(registry_path)
    issues = validate_registry(payload)
    if issues:
        raise RegistryError(validation_message(issues))
    filtered_sources = sources_matching_topics(enabled_sources(payload), topics)
    channels = [channel_value(source) for source in filtered_sources]
    channels = [channel for channel in channels if channel]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(channels) + ("\n" if channels else ""), encoding="utf-8")
    return {
        "registry_path": str(registry_path),
        "output_path": str(output),
        "exported_count": len(channels),
        "topics": normalize_topics(topics),
    }


def registry_sources(registry_path: Path) -> dict:
    payload = load_registry(registry_path, missing_ok=True)
    issues = validate_registry(payload)
    if issues:
        raise RegistryError(validation_message(issues))
    sources = payload.get("sources", [])
    topics: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            continue
        topics.update(normalize_topics(source.get("topics") or []))
    return {
        "registry_path": str(registry_path),
        "source_count": len(sources),
        "enabled_count": len(enabled_sources(payload)),
        "topics": sorted(topics),
        "sources": sources,
    }


def update_source_enabled(registry_path: Path, *, source_id: str, enabled: bool) -> dict:
    payload = load_registry(registry_path)
    issues = validate_registry(payload)
    if issues:
        raise RegistryError(validation_message(issues))
    for source in payload.get("sources", []):
        if not isinstance(source, dict):
            continue
        if source.get("source_id") == source_id:
            source["enabled"] = enabled
            save_registry(registry_path, payload)
            return source
    raise RegistryError(f"Source not found: {source_id}")


def update_source_topics(registry_path: Path, *, source_id: str, topics: list[str]) -> dict:
    normalized_topics = normalize_topics(topics)
    payload = load_registry(registry_path)
    issues = validate_registry(payload)
    if issues:
        raise RegistryError(validation_message(issues))
    for source in payload.get("sources", []):
        if not isinstance(source, dict):
            continue
        if source.get("source_id") == source_id:
            source["topics"] = list(normalized_topics)
            issues = validate_registry(payload)
            if issues:
                raise RegistryError(validation_message(issues))
            save_registry(registry_path, payload)
            return source
    raise RegistryError(f"Source not found: {source_id}")


def remove_sources(registry_path: Path, *, source_ids: list[str]) -> dict:
    payload = load_registry(registry_path)
    issues = validate_registry(payload)
    if issues:
        raise RegistryError(validation_message(issues))
    requested = set(source_ids)
    if not requested:
        raise RegistryError("Select at least one source to remove")
    before = len(payload.get("sources", []))
    payload["sources"] = [
        source
        for source in payload.get("sources", [])
        if not isinstance(source, dict) or source.get("source_id") not in requested
    ]
    removed_count = before - len(payload.get("sources", []))
    if removed_count == 0:
        raise RegistryError("No matching sources were removed")
    save_registry(registry_path, payload)
    return {
        "registry_path": str(registry_path),
        "removed_count": removed_count,
        "source_count": len(payload.get("sources", [])),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Maintain a private T-Sense source registry.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_registry_arg(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--source-registry", type=Path, default=default_registry_path())
        agent_cli.add_format_argument(subparser)

    import_parser = subparsers.add_parser("import-list", help="Import a legacy channel list.")
    import_parser.add_argument("channel_list", type=Path)
    import_parser.add_argument("--dry-run", action="store_true")
    import_parser.add_argument(
        "--topic",
        action="append",
        default=[],
        help="Attach a topic tag to imported sources. Repeat for multiple topics.",
    )
    add_registry_arg(import_parser)

    validate_parser = subparsers.add_parser("validate", help="Validate a source registry.")
    add_registry_arg(validate_parser)

    list_parser = subparsers.add_parser("list", help="List registry sources.")
    list_parser.add_argument("--topic", action="append", default=[], help="Filter sources by topic tag.")
    add_registry_arg(list_parser)

    export_parser = subparsers.add_parser("export-list", help="Export enabled sources as a channel list.")
    export_parser.add_argument("--output", required=True, type=Path)
    export_parser.add_argument("--topic", action="append", default=[], help="Filter exported sources by topic tag.")
    add_registry_arg(export_parser)
    return parser


def _emit_result(args: argparse.Namespace, data: dict) -> None:
    if agent_cli.is_json_format(args):
        agent_cli.print_json(agent_cli.envelope_success(data))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


def _emit_registry_error(args: argparse.Namespace, issues: list[str], message: str) -> None:
    agent_cli.emit_error(
        args,
        code="registry_invalid",
        message=message,
        retryable=False,
        next_step="Fix the source registry JSON, then rerun validate.",
        details={"issues": issues},
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    registry_path = Path(args.source_registry)

    try:
        if args.command == "import-list":
            data = import_channel_list(
                args.channel_list,
                registry_path,
                dry_run=args.dry_run,
                topics=args.topic,
            )
            _emit_result(args, data)
            return agent_cli.EXIT_SUCCESS

        payload = load_registry(registry_path)
        issues = validate_registry(payload)
        if issues:
            _emit_registry_error(args, issues, validation_message(issues))
            return agent_cli.EXIT_VALIDATION

        if args.command == "validate":
            _emit_result(
                args,
                {
                    "registry_path": str(registry_path),
                    "source_count": len(payload.get("sources", [])),
                    "enabled_count": len(enabled_sources(payload)),
                    "issues": [],
                },
            )
            return agent_cli.EXIT_SUCCESS

        if args.command == "list":
            listed_sources = sources_matching_topics(payload.get("sources", []), args.topic)
            _emit_result(
                args,
                {
                    "registry_path": str(registry_path),
                    "sources": listed_sources,
                    "source_count": len(listed_sources),
                    "enabled_count": len(sources_matching_topics(enabled_sources(payload), args.topic)),
                    "total_source_count": len(payload.get("sources", [])),
                    "topics": normalize_topics(args.topic),
                },
            )
            return agent_cli.EXIT_SUCCESS

        if args.command == "export-list":
            _emit_result(args, export_channel_list(registry_path, args.output, topics=args.topic))
            return agent_cli.EXIT_SUCCESS
    except OSError as exc:
        agent_cli.emit_error(
            args,
            code="registry_io_error",
            message=str(exc),
            retryable=False,
            next_step="Check the path and file permissions.",
        )
        return agent_cli.EXIT_VALIDATION
    except RegistryError as exc:
        agent_cli.emit_error(
            args,
            code="registry_invalid",
            message=str(exc),
            retryable=False,
            next_step="Run source_registry.py validate and fix the registry.",
        )
        return agent_cli.EXIT_VALIDATION

    agent_cli.emit_error(
        args,
        code="unknown_command",
        message=f"Unsupported command: {args.command}",
        retryable=False,
        next_step="Use --help to inspect supported commands.",
    )
    return agent_cli.EXIT_VALIDATION


if __name__ == "__main__":
    raise SystemExit(main())
