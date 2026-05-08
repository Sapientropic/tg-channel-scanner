"""Local JSON state for cross-run decision intelligence.

The state file is deliberately small and explicit.  It stores durable item
identity and counters, but never raw Telegram text or feedback note bodies.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable


SCHEMA_VERSION = "item_memory_v1"
STATE_FILENAME = "item-memory.json"


class StateStoreError(Exception):
    """Raised when local state cannot be safely loaded or saved."""


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def item_memory_path(state_dir: Path | str) -> Path:
    return Path(state_dir) / STATE_FILENAME


def default_item_memory() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": None,
        "items": {},
    }


def _validate_item_memory(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise StateStoreError("Item memory root must be an object.")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise StateStoreError(f"Item memory schema_version must be {SCHEMA_VERSION}.")
    if not isinstance(payload.get("items"), dict):
        raise StateStoreError("Item memory must contain an items object.")
    payload.setdefault("updated_at", None)
    return payload


def load_item_memory(state_dir: Path | str) -> dict:
    path = item_memory_path(state_dir)
    if not path.exists():
        return default_item_memory()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StateStoreError(f"Item memory is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise StateStoreError(f"Could not read item memory: {exc}") from exc
    return _validate_item_memory(payload)


def save_item_memory(state_dir: Path | str, state: dict) -> Path:
    payload = _validate_item_memory(state)
    payload["updated_at"] = utc_now()
    path = item_memory_path(state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(tmp_path, path)
    except OSError as exc:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise StateStoreError(f"Could not write item memory: {exc}") from exc
    return path


def load_feedback_jsonl(paths: Iterable[Path | str] | None) -> list[dict]:
    entries: list[dict] = []
    for path_value in paths or []:
        path = Path(path_value)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError as exc:
            raise StateStoreError(f"Could not read feedback JSONL {path}: {exc}") from exc
        for line_no, raw in enumerate(lines, start=1):
            text = raw.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                raise StateStoreError(
                    f"Feedback JSONL {path}:{line_no} is not valid JSON: {exc}"
                ) from exc
            if not isinstance(payload, dict):
                raise StateStoreError(f"Feedback JSONL {path}:{line_no} must be an object.")
            entries.append(payload)
    return entries
