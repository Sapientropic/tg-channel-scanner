"""Support and diagnostics status for the local Signal Desk app."""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path


DESK_SUPPORT_STATUS_SCHEMA_VERSION = "desk_support_status_v1"
DESK_SUPPORT_DIAGNOSTIC_EXPORT_SCHEMA_VERSION = "desk_support_diagnostic_export_v1"
DESK_SUPPORT_READINESS_SCHEMA_VERSION = "desk_support_readiness_v1"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_timestamp(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z._-]+", "-", value).strip("-") or "snapshot"


def _path_status(label: str, path: Path, *, detail: str, target: str | None = None) -> dict:
    payload = {
        "label": label,
        "path": str(path.expanduser()),
        "exists": path.expanduser().exists(),
        "detail": detail,
    }
    if target:
        payload["target"] = target
    return payload


def _same_path(left: Path, right: Path) -> bool:
    try:
        return left.expanduser().resolve() == right.expanduser().resolve()
    except OSError:
        return left.expanduser() == right.expanduser()


def default_legacy_telegram_config_dir() -> Path:
    home = Path(os.environ.get("HOME") or os.environ.get("USERPROFILE") or "~").expanduser()
    return home / ".config" / "tgcli"


def default_desktop_log_path() -> Path:
    configured = os.environ.get("TSENSE_DESKTOP_LOG")
    if configured:
        return Path(configured).expanduser()
    home = Path(os.environ.get("HOME") or os.environ.get("USERPROFILE") or "~").expanduser()
    return home / "Library" / "Logs" / "T-Sense" / "desktop-backend.log"


def _legacy_locations(
    *,
    state_root: Path,
    code_root: Path,
    telegram_dir: Path,
    legacy_telegram_config_dir: Path | None = None,
) -> list[dict]:
    locations: list[dict] = []
    if not _same_path(state_root, code_root):
        candidates = [
            (
                "Legacy project state",
                code_root / ".tgcs",
                "Profile registry, source list, review DB, or scheduler state from a project-local setup.",
            ),
            (
                "Legacy reports",
                code_root / "output",
                "Reports, scan metadata, and feedback exports created before the macOS app moved state into Application Support.",
            ),
        ]
        locations.extend(_path_status(label, path, detail=detail) for label, path, detail in candidates if path.expanduser().exists())

    legacy_telegram_dir = legacy_telegram_config_dir or default_legacy_telegram_config_dir()
    if not _same_path(legacy_telegram_dir, telegram_dir) and legacy_telegram_dir.exists():
        locations.append(
            _path_status(
                "Legacy Telegram session",
                legacy_telegram_dir,
                detail="Telegram credentials or session files from the older default tgcli location.",
            )
        )
    return locations


def _migration_status(
    *,
    state_root: Path,
    code_root: Path,
    telegram_dir: Path,
    legacy_telegram_config_dir: Path | None = None,
) -> dict:
    locations = _legacy_locations(
        state_root=state_root,
        code_root=code_root,
        telegram_dir=telegram_dir,
        legacy_telegram_config_dir=legacy_telegram_config_dir,
    )
    if locations:
        return {
            "schema_version": "desk_support_migration_v1",
            "status": "manual_required",
            "detail": "Older project-local data was found outside the active app data folder.",
            "next_action": "Use a user-selected source folder before migrating any legacy data into the macOS app workspace.",
            "legacy_locations": locations,
        }
    return {
        "schema_version": "desk_support_migration_v1",
        "status": "no_legacy_data",
        "detail": "No legacy project-local data was found from this app context.",
        "next_action": "No migration action is needed.",
        "legacy_locations": [],
    }


def _support_target_paths(
    *,
    project_root: Path,
    db_path: Path,
    telegram_config_dir: Path,
    source_registry_path: Path | None = None,
    desktop_log_path: Path | None = None,
) -> dict[str, Path]:
    state_root = project_root.expanduser()
    log_path = desktop_log_path or default_desktop_log_path()
    telegram_dir = telegram_config_dir.expanduser()
    return {
        "app_data_root": state_root,
        "output_dir": state_root / "output",
        "database": db_path.expanduser(),
        "source_registry": (source_registry_path or state_root / ".tgcs" / "sources.json").expanduser(),
        "desktop_log": log_path.expanduser(),
        "telegram_config": telegram_dir,
    }


def _list_value(value: object) -> list:
    return value if isinstance(value, list) else []


def _dict_value(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _readiness_item(label: str, status: str, detail: str, next_action: str = "") -> dict:
    payload = {
        "label": label,
        "status": status,
        "detail": detail,
    }
    if next_action:
        payload["next_action"] = next_action
    return payload


def real_scan_readiness(
    *,
    telegram_status: dict | None = None,
    sources_result: dict | None = None,
    dashboard_state: dict | None = None,
    demo_report_exists: bool = False,
) -> dict:
    """Return a secret-free checklist for a user-run real scan acceptance pass."""
    telegram = _dict_value(telegram_status)
    sources = _dict_value(sources_result)
    state = _dict_value(dashboard_state)
    profile_count = len(_list_value(state.get("profiles")))
    run_count = len(_list_value(state.get("runs")))
    try:
        source_count = int(sources.get("enabled_count") or sources.get("source_count") or 0)
    except (TypeError, ValueError):
        source_count = 0
    telegram_ready = bool(telegram.get("credentials_ready") and telegram.get("session_ready"))
    ready_count = sum(
        [
            bool(demo_report_exists),
            profile_count > 0,
            telegram_ready,
            source_count > 0,
            run_count > 0,
        ]
    )
    total_count = 5
    items = [
        _readiness_item(
            "Demo report",
            "ready" if demo_report_exists else "needs_user",
            "A local sample report is available." if demo_report_exists else "Generate the local sample report first.",
            "" if demo_report_exists else "Use Start > Generate demo report.",
        ),
        _readiness_item(
            "Profile",
            "ready" if profile_count > 0 else "needs_user",
            f"{profile_count} profile{'' if profile_count == 1 else 's'} saved."
            if profile_count > 0
            else "No saved profile is available yet.",
            "" if profile_count > 0 else "Create a profile from a plain-language goal.",
        ),
        _readiness_item(
            "Telegram login",
            "ready" if telegram_ready else "needs_user",
            "Telegram credentials and the local session are ready."
            if telegram_ready
            else "Telegram is not fully authorized on this Mac yet.",
            "" if telegram_ready else "Finish Telegram setup before scanning private sources.",
        ),
        _readiness_item(
            "Authorized sources",
            "ready" if source_count > 0 else "needs_user",
            f"{source_count} enabled source{'' if source_count == 1 else 's'} available."
            if source_count > 0
            else "No enabled source is saved yet.",
            "" if source_count > 0 else "Add at least one Telegram source you can access.",
        ),
        _readiness_item(
            "First real report",
            "ready" if run_count > 0 else "needs_user",
            f"{run_count} run{'' if run_count == 1 else 's'} found."
            if run_count > 0
            else "No real report run is recorded yet.",
            "" if run_count > 0 else "Run one real report after Telegram and sources are ready.",
        ),
    ]
    return {
        "schema_version": DESK_SUPPORT_READINESS_SCHEMA_VERSION,
        "status": "ready" if ready_count == total_count else "needs_user",
        "ready_count": ready_count,
        "total_count": total_count,
        "summary": f"{ready_count}/{total_count} real-scan checks ready.",
        "items": items,
    }


def _default_reveal_opener(path: Path) -> None:
    target = path.expanduser()
    opener_target = target
    if not opener_target.exists():
        opener_target = target.parent
        opener_target.mkdir(parents=True, exist_ok=True)
    if platform.system() == "Darwin":
        args = ["open", "-R", str(target)] if target.exists() and target.is_file() else ["open", str(opener_target)]
    elif os.name == "nt":
        args = ["explorer", "/select,", str(target)] if target.exists() and target.is_file() else ["explorer", str(opener_target)]
    else:
        args = ["xdg-open", str(opener_target)]
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def reveal_support_target(
    target: object,
    *,
    project_root: Path,
    db_path: Path,
    telegram_config_dir: Path,
    source_registry_path: Path | None = None,
    desktop_log_path: Path | None = None,
    opener: Callable[[Path], None] = _default_reveal_opener,
) -> dict:
    target_id = str(target or "").strip()
    paths = _support_target_paths(
        project_root=project_root,
        db_path=db_path,
        telegram_config_dir=telegram_config_dir,
        source_registry_path=source_registry_path,
        desktop_log_path=desktop_log_path,
    )
    selected = paths.get(target_id)
    if selected is None:
        raise ValueError("Unsupported support path target.")
    opener(selected)
    return {
        "schema_version": "desk_support_reveal_result_v1",
        "target": target_id,
        "path": str(selected.expanduser()),
        "opened": True,
    }


def _diagnostic_export_target(*, project_root: Path, exported_at: str, output_path: Path | None = None) -> Path:
    state_root = project_root.expanduser()
    target = output_path or state_root / "output" / "diagnostics" / f"t-sense-support-{_safe_timestamp(exported_at)}.json"
    if not target.is_absolute():
        target = state_root / target
    resolved = target.expanduser().resolve()
    try:
        resolved.relative_to(state_root.resolve())
    except ValueError as exc:
        raise ValueError("support_diagnostic_export_path_outside_app_data") from exc
    return resolved


def write_support_diagnostic_export(
    *,
    project_root: Path,
    code_root: Path,
    db_path: Path,
    telegram_config_dir: Path,
    dashboard_url: str,
    source_registry_path: Path | None = None,
    desktop_log_path: Path | None = None,
    legacy_telegram_config_dir: Path | None = None,
    readiness: dict | None = None,
    output_path: Path | None = None,
    now_fn: Callable[[], str] = _utc_now,
) -> dict:
    """Write a support snapshot without copying logs, DB rows, sessions, or report text."""
    exported_at = now_fn()
    status = desk_support_status(
        project_root=project_root,
        code_root=code_root,
        db_path=db_path,
        telegram_config_dir=telegram_config_dir,
        dashboard_url=dashboard_url,
        source_registry_path=source_registry_path,
        desktop_log_path=desktop_log_path,
        legacy_telegram_config_dir=legacy_telegram_config_dir,
        readiness=readiness,
        now_fn=lambda: exported_at,
    )
    target = _diagnostic_export_target(project_root=project_root, exported_at=exported_at, output_path=output_path)
    payload = {
        "schema_version": DESK_SUPPORT_DIAGNOSTIC_EXPORT_SCHEMA_VERSION,
        "exported_at": exported_at,
        "output_path": str(target),
        "status": status,
        "included": [
            {
                "label": "support status",
                "detail": "App paths, existence flags, platform, readiness checks, migration hints, data boundaries, and recovery guidance.",
            }
        ],
        "excluded": [
            {
                "label": "secrets",
                "detail": "API keys, tokens, Telegram auth codes, and session contents are not read or copied.",
            },
            {
                "label": "raw private text",
                "detail": "Telegram messages, database rows, report contents, and backend log contents are not copied.",
            },
        ],
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "schema_version": DESK_SUPPORT_DIAGNOSTIC_EXPORT_SCHEMA_VERSION,
        "output_path": str(target),
        "exported_at": exported_at,
    }


def desk_support_status(
    *,
    project_root: Path,
    code_root: Path,
    db_path: Path,
    telegram_config_dir: Path,
    dashboard_url: str,
    source_registry_path: Path | None = None,
    desktop_log_path: Path | None = None,
    legacy_telegram_config_dir: Path | None = None,
    readiness: dict | None = None,
    now_fn: Callable[[], str] = _utc_now,
) -> dict:
    """Return a secret-free support snapshot for the local dashboard UI."""
    state_root = project_root.expanduser()
    code_root = code_root.expanduser()
    output_dir = state_root / "output"
    registry_path = source_registry_path or state_root / ".tgcs" / "sources.json"
    log_path = desktop_log_path or default_desktop_log_path()
    telegram_dir = telegram_config_dir.expanduser()

    payload = {
        "schema_version": DESK_SUPPORT_STATUS_SCHEMA_VERSION,
        "app_data_root": str(state_root),
        "code_root": str(code_root),
        "database_path": str(db_path.expanduser()),
        "output_dir": str(output_dir),
        "source_registry_path": str(registry_path.expanduser()),
        "telegram_config_dir": str(telegram_dir),
        "desktop_log_path": str(log_path.expanduser()),
        "dashboard_url": dashboard_url,
        "platform": platform.platform(),
        "checked_at": now_fn(),
        "migration": _migration_status(
            state_root=state_root,
            code_root=code_root,
            telegram_dir=telegram_dir,
            legacy_telegram_config_dir=legacy_telegram_config_dir,
        ),
        "paths": [
            _path_status(
                "Local data",
                state_root,
                detail="Profiles, sources, database, Telegram session, reports, and review choices live here.",
                target="app_data_root",
            ),
            _path_status(
                "Reports",
                output_dir,
                detail="Generated demo reports, AI review reports, scan metadata, and feedback exports.",
                target="output_dir",
            ),
            _path_status(
                "Backend log",
                log_path,
                detail="Desktop launch, backend stdout, and backend stderr for startup or crash diagnosis.",
                target="desktop_log",
            ),
            _path_status(
                "Telegram session",
                telegram_dir,
                detail="Telegram credentials and local session files. Token values are not shown here.",
                target="telegram_config",
            ),
        ],
        "data_boundaries": [
            {
                "label": "Local state",
                "detail": "Profiles, source lists, review decisions, reports, and Telegram sessions stay on this Mac by default.",
                "external": False,
            },
            {
                "label": "AI requests",
                "detail": "When an AI review or AI assistant runs, selected scan text and configured image/OCR inputs can be sent to the chosen AI provider.",
                "external": True,
            },
            {
                "label": "Telegram access",
                "detail": "Scans use the locally authorized Telegram session and only the saved or selected sources.",
                "external": True,
            },
            {
                "label": "No hosted sync",
                "detail": "The desktop MVP does not upload the workspace to a T-Sense hosted account.",
                "external": False,
            },
        ],
        "recovery": [
            {
                "label": "Backend will not start",
                "detail": "Check the backend log first, then retry from the launcher window after fixing the reported port, Python, or package error.",
                "path": str(log_path.expanduser()),
            },
            {
                "label": "Telegram login fails",
                "detail": "Check whether credentials and session files exist under the Telegram session folder, then retry login from Start.",
                "path": str(telegram_dir),
            },
            {
                "label": "Report missing",
                "detail": "Open the Reports path and confirm the latest run or demo artifact exists before rerunning the review.",
                "path": str(output_dir),
            },
        ],
    }
    if readiness:
        payload["readiness"] = readiness
    return payload
