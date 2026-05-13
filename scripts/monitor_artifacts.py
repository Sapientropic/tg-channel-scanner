"""Monitor artifact naming, metadata, and scan sidecar helpers."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from scripts import monitor_state
    from scripts.monitor_config import PROJECT_ROOT, relative_to_root
    from scripts.profile_schema import parse_profile_config
except ModuleNotFoundError:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts import monitor_state
    from scripts.monitor_config import PROJECT_ROOT, relative_to_root
    from scripts.profile_schema import parse_profile_config



def file_hash(path: Path | None) -> str | None:
    if path is None or not path.exists() or not path.is_file():
        return None
    return monitor_state.sha256_text(path.read_text(encoding="utf-8"))



def safe_slug(value: str, fallback: str = "artifact") -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned or fallback



def profile_display_name(profile_id: str | None) -> str:
    slug = safe_slug(profile_id or "profile", fallback="profile")
    return " ".join(part.capitalize() for part in slug.split("-"))



def report_stamp_from_run_id(run_id_value: str) -> str:
    match = re.match(r"^run_(\d{8})T(\d{6})Z", run_id_value)
    if not match:
        return safe_slug(run_id_value, fallback="latest")
    stamp = f"{match.group(1)}T{match.group(2)}Z"
    try:
        parsed = datetime.strptime(stamp, "%Y%m%dT%H%M%SZ")
    except ValueError:
        return safe_slug(run_id_value, fallback="latest")
    return parsed.strftime("%Y-%m-%d-%H%M")



def report_title_for_profile(profile_file: Path, profile_id: str) -> str:
    try:
        profile_config = parse_profile_config(profile_file.read_text(encoding="utf-8"))
    except OSError:
        return f"{profile_display_name(profile_id)} Report"
    title = profile_config.labels.report_title.strip()
    return title or f"{profile_display_name(profile_id)} Report"



def report_file_stem(profile_id: str, run_id_value: str, *, report_title: str | None = None) -> str:
    label = report_title or f"{profile_display_name(profile_id)} Report"
    return f"{safe_slug(label, fallback='report')}-{report_stamp_from_run_id(run_id_value)}"



def report_output_paths(
    run_dir: Path,
    *,
    profile_id: str,
    run_id_value: str,
    report_title: str | None = None,
) -> tuple[Path, Path]:
    stem = report_file_stem(profile_id, run_id_value, report_title=report_title)
    return run_dir / f"{stem}.md", run_dir / f"{stem}.html"



def artifact_display_metadata(
    artifact_type: str,
    path: Path,
    *,
    profile_id: str | None = None,
    report_title: str | None = None,
) -> dict[str, str]:
    if artifact_type == "report_html":
        return {
            "category": "reports",
            "format": "HTML",
            "display_name": report_title or f"{profile_display_name(profile_id)} Report",
            "display_path": f"Reports/{path.name}",
        }
    if artifact_type == "report_markdown":
        return {
            "category": "reports",
            "format": "Markdown",
            "display_name": report_title or f"{profile_display_name(profile_id)} Report",
            "display_path": f"Reports/{path.name}",
        }
    if artifact_type in {"scan", "raw_scan", "scan_meta", "scan_errors"}:
        return {
            "category": "internal",
            "format": path.suffix.lstrip(".").upper() or "DATA",
            "display_name": artifact_type.replace("_", " ").title(),
            "display_path": f"Internal/{path.name}",
        }
    return {
        "category": "artifacts",
        "format": path.suffix.lstrip(".").upper() or "DATA",
        "display_name": artifact_type.replace("_", " ").title(),
        "display_path": f"Artifacts/{path.name}",
    }



def artifact(
    path: Path,
    artifact_type: str,
    *,
    profile_id: str | None = None,
    run_id: str | None = None,
    report_title: str | None = None,
) -> dict[str, Any]:
    metadata = artifact_display_metadata(artifact_type, path, profile_id=profile_id, report_title=report_title)
    return {
        "artifact_id": f"{artifact_type}:{path.name}",
        "type": artifact_type,
        "path": relative_to_root(path),
        "sha256": file_hash(path),
        "run_id": run_id or "",
        **metadata,
    }



def scan_sidecar_paths(scan_path: Path | None, run_dir: Path) -> tuple[Path, Path]:
    base = scan_path or (run_dir / "scan.jsonl")
    return base.with_suffix(".meta.json"), base.with_suffix(".errors.log")



def load_scan_meta(scan_path: Path | None, run_dir: Path) -> dict[str, Any]:
    meta_path, _ = scan_sidecar_paths(scan_path, run_dir)
    if not meta_path.exists():
        return {}
    try:
        payload = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}



def diagnostics_from_scan_meta(meta: dict[str, Any]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    failure_count = int(meta.get("failure_count") or 0)
    failed_channels = meta.get("failed_channels") if isinstance(meta.get("failed_channels"), list) else []
    source_health = meta.get("source_health") if isinstance(meta.get("source_health"), list) else []
    if failure_count:
        hint = ", ".join(str(channel) for channel in failed_channels[:5]) or f"{failure_count} channels"
        reason_counts = Counter(
            str(row.get("failure_reason") or row.get("failure") or "access_error")
            for row in source_health
            if isinstance(row, dict) and row.get("failure")
        )
        reason_hint = ", ".join(
            f"{reason.replace('_', ' ')} {count}"
            for reason, count in sorted(reason_counts.items(), key=lambda item: (-item[1], item[0]))[:3]
        )
        if reason_hint:
            hint = f"{hint}. Top reasons: {reason_hint}"
        diagnostics.append(
            {
                "code": "channel_failures",
                "severity": "warning",
                "message": f"{failure_count} channels failed during scan: {hint}.",
                "next_step": "Open Start > Check source access, then pause inaccessible sources or inspect scan.errors.log.",
            }
        )
    if int(meta.get("total_messages_collected") or 0) == 0:
        diagnostics.append(
            {
                "code": "no_messages_fetched",
                "severity": "failure",
                "message": "No Telegram messages were fetched for this monitor run.",
                "next_step": "Check source names, login/session state, scan window, and scan.errors.log.",
            }
        )
    return diagnostics



def parse_message_date(value: object) -> datetime | None:
    return monitor_state.parse_iso_datetime(value)



def source_ref_dates(scan_path: Path | None) -> dict[tuple[str, object], str]:
    if not scan_path or not scan_path.exists():
        return {}
    refs: dict[tuple[str, object], str] = {}
    with scan_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(message, dict):
                continue
            channel = str(message.get("channel") or "").strip()
            msg_id = message.get("id")
            parsed = parse_message_date(message.get("date"))
            if channel and msg_id is not None and parsed is not None:
                stamped = parsed.isoformat().replace("+00:00", "Z")
                refs[(channel, msg_id)] = stamped
                refs[(channel, str(msg_id))] = stamped
    return refs



def annotate_items_with_source_freshness(items: list[dict[str, Any]], scan_path: Path | None) -> list[dict[str, Any]]:
    dates_by_ref = source_ref_dates(scan_path)
    if not dates_by_ref:
        return items
    annotated: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        dates = []
        for ref in item.get("source_message_refs") or []:
            if not isinstance(ref, dict):
                continue
            channel = str(ref.get("channel") or "").strip()
            msg_id = ref.get("id")
            if (channel, msg_id) in dates_by_ref:
                dates.append(dates_by_ref[(channel, msg_id)])
        if not dates:
            annotated.append(item)
            continue
        copy = dict(item)
        freshness = dict(copy.get("monitor_freshness") or {})
        freshness["freshest_source_at"] = max(dates)
        copy["monitor_freshness"] = freshness
        annotated.append(copy)
    return annotated
