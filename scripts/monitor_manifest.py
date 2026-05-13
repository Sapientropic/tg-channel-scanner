"""Run manifest and monitor-result payload construction."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

try:
    from scripts.monitor_artifacts import artifact, file_hash, report_title_for_profile, scan_sidecar_paths
    from scripts.monitor_config import RUN_MANIFEST_SCHEMA_VERSION, alert_rule_for_profile, relative_to_root
except ModuleNotFoundError:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.monitor_artifacts import artifact, file_hash, report_title_for_profile, scan_sidecar_paths
    from scripts.monitor_config import RUN_MANIFEST_SCHEMA_VERSION, alert_rule_for_profile, relative_to_root


def collect_run_artifacts(
    *,
    profile_file: Path,
    profile_id: str,
    run_id: str,
    run_dir: Path,
    scan_path: Path | None,
    raw_scan_path: Path | None,
    report_path: Path | None,
    html_path: Path | None,
) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    report_title = report_title_for_profile(profile_file, profile_id)
    if raw_scan_path and raw_scan_path.exists() and raw_scan_path != scan_path:
        artifacts.append(artifact(raw_scan_path, "raw_scan", profile_id=profile_id, run_id=run_id))
    for path, kind in ((scan_path, "scan"), (report_path, "report_markdown"), (html_path, "report_html")):
        if path and path.exists():
            artifacts.append(
                artifact(
                    path,
                    kind,
                    profile_id=profile_id,
                    run_id=run_id,
                    report_title=report_title,
                )
            )
    meta_path, errors_path = scan_sidecar_paths(raw_scan_path or scan_path, run_dir)
    if meta_path.exists():
        artifacts.append(artifact(meta_path, "scan_meta", profile_id=profile_id, run_id=run_id))
    if errors_path.exists():
        artifacts.append(artifact(errors_path, "scan_errors", profile_id=profile_id, run_id=run_id))
    return artifacts


def semantic_manifest(
    *,
    max_messages: int | None,
    max_tokens: int | None,
    batch_size: int | None,
    concurrency: int | None,
) -> dict[str, Any]:
    return {
        "max_messages": max_messages,
        "max_tokens": max_tokens,
        "batch_size": batch_size,
        "concurrency": concurrency or 1,
    }


def scan_manifest(
    *,
    concurrency: int | None,
    delay_seconds: float | None,
) -> dict[str, Any]:
    manifest: dict[str, Any] = {"concurrency": concurrency or 1}
    if delay_seconds is not None:
        manifest["delay_seconds"] = delay_seconds
    return manifest


def build_run_manifest(
    *,
    run_id: str,
    profile_id: str,
    profile: dict[str, Any],
    profile_file: Path,
    source_registry: Path,
    scan_window_hours: int,
    scan: dict[str, Any],
    semantic: dict[str, Any],
    delivery_enabled: bool,
    delivery_suppressed_reason: str,
    prefilter_context: dict[str, Any],
    status: str,
    started_at: str,
    completed_at: str,
    artifacts: list[dict[str, Any]],
    alert_count: int,
    review_card_count: int,
    diagnostics: list[dict[str, Any]],
    exit_code: int,
    stderr: str,
    llm_payload: dict[str, Any] | None,
    alert_events: list[dict[str, Any]],
    command: list[str | Path],
    commands_executed: list[list[str | Path]],
) -> dict[str, Any]:
    return {
        "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
        "run_id": run_id,
        "profile_id": profile_id,
        "profile_path": relative_to_root(profile_file),
        "profile_hash": file_hash(profile_file),
        "source_registry_path": relative_to_root(source_registry) if source_registry.exists() else None,
        "source_registry_hash": file_hash(source_registry) if source_registry.exists() else None,
        "scan_window": {"hours": scan_window_hours},
        "scan": scan,
        "source_filters": {
            "topics": profile.get("source_topics") or profile.get("topics") or [],
            "source_ids": profile.get("source_ids") or [],
        },
        "alert_rule": alert_rule_for_profile(profile),
        "semantic": semantic,
        "alert_schedule": {
            "mode": profile.get("alert_schedule_mode") or "work_hours",
            "delivery_enabled": delivery_enabled,
            "suppressed_reason": "" if delivery_enabled else delivery_suppressed_reason,
        },
        "prefilter": prefilter_context,
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "artifacts": artifacts,
        "report_status": status,
        "alert_count": alert_count,
        "review_card_count": review_card_count,
        "diagnostics": diagnostics,
        "error_summary": None if exit_code == 0 else {"exit_code": exit_code, "stderr": stderr[-2000:]},
        "llm": llm_payload,
        "delivery_attempts": [event["delivery_attempt"] for event in alert_events],
        "command": [str(part) for part in command],
        "commands": [[str(part) for part in command] for command in commands_executed],
    }


def write_run_manifest(run_dir: Path, manifest: dict[str, Any]) -> Path:
    manifest_path = run_dir / "run-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def monitor_run_result_data(
    *,
    status: str,
    run_id: str,
    manifest_path: Path,
    db_path: Path,
    report_path: Path | None,
    html_path: Path | None,
    review_card_count: int,
    alert_count: int,
    prefilter_context: dict[str, Any],
    semantic: dict[str, Any],
    diagnostics: list[dict[str, Any]],
    llm_payload: dict[str, Any] | None,
    alert_events: list[dict[str, Any]],
    report_data: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "monitor_run_result_v1",
        "status": status,
        "run_id": run_id,
        "manifest_path": relative_to_root(manifest_path),
        "db_path": relative_to_root(db_path),
        "report_path": relative_to_root(report_path) if report_path else None,
        "html_path": relative_to_root(html_path) if html_path else None,
        "review_card_count": review_card_count,
        "alert_count": alert_count,
        "prefilter": prefilter_context,
        "semantic": semantic,
        "diagnostics": diagnostics,
        "llm": llm_payload,
        "delivery_attempts": [event["delivery_attempt"] for event in alert_events],
        "extraction_request_path": report_data.get("extraction_request_path") or report_data.get("request_path"),
        "items_output_path": report_data.get("items_output_path"),
    }
