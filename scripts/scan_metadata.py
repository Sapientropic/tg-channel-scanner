"""Scan metadata sidecar helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path



def meta_path_for_output(output_path: Path) -> Path:
    return output_path.with_suffix(".meta.json")



def build_scan_metadata(
    *,
    started_at: datetime,
    completed_at: datetime,
    cutoff: datetime,
    channel_list_path: Path,
    channels: list[str],
    output_path: Path,
    errors_path: Path,
    total_written: int,
    failed_channels: list[str],
    incomplete_channels: list[str],
    total_ocr: int,
    ocr_enabled: bool,
    hours: int,
    source_health: list[dict] | None = None,
    source_registry_path: Path | None = None,
) -> dict:
    payload = {
        "scan_date": started_at.astimezone(UTC).date().isoformat(),
        "scan_started_at": started_at.astimezone(UTC).isoformat(),
        "scan_completed_at": completed_at.astimezone(UTC).isoformat(),
        "scan_window": f"Last {hours} hours",
        "cutoff": cutoff.astimezone(UTC).isoformat(),
        "channel_list_path": str(channel_list_path),
        "channels": channels,
        "channel_count": len(channels),
        "total_messages_collected": total_written,
        "failed_channels": failed_channels,
        "failure_count": len(failed_channels),
        "incomplete_channels": incomplete_channels,
        "incomplete_count": len(incomplete_channels),
        "ocr_enabled": ocr_enabled,
        "ocr_count": total_ocr,
        "output_path": str(output_path),
        "errors_path": str(errors_path),
    }
    if source_registry_path:
        payload["source_registry_path"] = str(source_registry_path)
    if source_health is not None:
        payload["source_health"] = source_health
    return payload



def write_scan_metadata(path: Path, metadata: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
