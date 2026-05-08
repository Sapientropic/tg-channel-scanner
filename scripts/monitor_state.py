"""SQLite state for v0.5-alpha monitoring, inbox, alerts, and profile diffs.

The database is local private state under ``.tgcs/``.  It is allowed to keep
workflow notes and profile snapshots, but it must not become a second archive
of Telegram message bodies, credentials, bot tokens, or sessions.  Review cards
therefore keep source refs and extracted decision fields only.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable


DB_FILENAME = "tgcs.db"
STATE_SCHEMA_VERSION = "monitor_state_v1"
REVIEW_CARD_SCHEMA_VERSION = "review_card_v1"
ALERT_EVENT_SCHEMA_VERSION = "alert_event_v1"
PROFILE_PATCH_SCHEMA_VERSION = "profile_patch_suggestion_v1"
DELIVERY_TARGET_SCHEMA_VERSION = "delivery_target_v1"

PENDING_STATUS = "pending"
HANDLED_STATUSES = {"kept", "skipped", "false_positive", "follow_up"}
REVIEW_ACTIONS = {"keep", "skip", "false_positive", "follow_up"}
ACTION_TO_STATUS = {
    "keep": "kept",
    "skip": "skipped",
    "false_positive": "false_positive",
    "follow_up": "follow_up",
}


class MonitorStateError(Exception):
    """Raised when monitor state cannot be loaded or updated safely."""


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def stable_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def parse_json(text: str | None, default: Any) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def connect(db_path: Path | str) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS profiles (
            profile_id TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 1,
            config_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS profile_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            profile_path TEXT NOT NULL,
            profile_hash TEXT NOT NULL,
            profile_text TEXT NOT NULL,
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            manifest_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS run_artifacts (
            artifact_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            artifact_type TEXT NOT NULL,
            path TEXT NOT NULL,
            sha256 TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS review_cards (
            card_id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            item_key TEXT NOT NULL,
            title TEXT NOT NULL,
            rating TEXT NOT NULL,
            decision_status TEXT NOT NULL,
            source_refs_json TEXT NOT NULL,
            item_json TEXT NOT NULL,
            status TEXT NOT NULL,
            first_run_id TEXT NOT NULL,
            last_run_id TEXT NOT NULL,
            report_path TEXT,
            dashboard_url TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            handled_at TEXT
        );

        CREATE TABLE IF NOT EXISTS feedback_events (
            event_id TEXT PRIMARY KEY,
            card_id TEXT,
            profile_id TEXT NOT NULL,
            action TEXT NOT NULL,
            note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            FOREIGN KEY(card_id) REFERENCES review_cards(card_id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS profile_patch_suggestions (
            patch_id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            card_id TEXT,
            note TEXT NOT NULL,
            status TEXT NOT NULL,
            diff_text TEXT NOT NULL,
            proposed_profile_text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            applied_at TEXT,
            FOREIGN KEY(card_id) REFERENCES review_cards(card_id) ON DELETE SET NULL
        );

        CREATE TABLE IF NOT EXISTS alert_events (
            alert_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            card_id TEXT NOT NULL,
            profile_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            status TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            delivery_attempt_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES runs(run_id) ON DELETE CASCADE,
            FOREIGN KEY(card_id) REFERENCES review_cards(card_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS delivery_targets (
            target_id TEXT PRIMARY KEY,
            target_type TEXT NOT NULL,
            enabled INTEGER NOT NULL DEFAULT 0,
            config_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
        (STATE_SCHEMA_VERSION, utc_now()),
    )
    conn.commit()


def upsert_profile(conn: sqlite3.Connection, config: dict[str, Any]) -> None:
    now = utc_now()
    conn.execute(
        """
        INSERT INTO profiles(profile_id, path, enabled, config_json, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(profile_id) DO UPDATE SET
            path = excluded.path,
            enabled = excluded.enabled,
            config_json = excluded.config_json,
            updated_at = excluded.updated_at
        """,
        (
            config["id"],
            str(config["path"]),
            1 if config.get("enabled", True) else 0,
            stable_json(config),
            now,
        ),
    )
    conn.commit()


def upsert_delivery_target(conn: sqlite3.Connection, target: dict[str, Any]) -> None:
    now = utc_now()
    sanitized = dict(target)
    sanitized.pop("token", None)
    sanitized.pop("bot_token", None)
    conn.execute(
        """
        INSERT INTO delivery_targets(target_id, target_type, enabled, config_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(target_id) DO UPDATE SET
            target_type = excluded.target_type,
            enabled = excluded.enabled,
            config_json = excluded.config_json,
            updated_at = excluded.updated_at
        """,
        (
            sanitized["id"],
            sanitized.get("type", "telegram_bot"),
            1 if sanitized.get("enabled", False) else 0,
            stable_json(sanitized),
            now,
            now,
        ),
    )
    conn.commit()


def record_run(conn: sqlite3.Connection, manifest: dict[str, Any]) -> None:
    run_id = manifest["run_id"]
    now = utc_now()
    conn.execute(
        """
        INSERT OR REPLACE INTO runs(run_id, profile_id, status, started_at, completed_at, manifest_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM runs WHERE run_id = ?), ?))
        """,
        (
            run_id,
            manifest["profile_id"],
            manifest.get("status", "complete"),
            manifest.get("started_at") or now,
            manifest.get("completed_at"),
            stable_json(manifest),
            run_id,
            now,
        ),
    )
    for artifact in manifest.get("artifacts", []):
        if not isinstance(artifact, dict) or not artifact.get("path"):
            continue
        conn.execute(
            """
            INSERT OR REPLACE INTO run_artifacts(artifact_id, run_id, artifact_type, path, sha256, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                artifact.get("artifact_id") or f"{run_id}:{artifact.get('type')}:{artifact.get('path')}",
                run_id,
                artifact.get("type") or "artifact",
                artifact.get("path"),
                artifact.get("sha256"),
                now,
            ),
        )
    conn.commit()


def _source_refs(item: dict[str, Any]) -> list[dict[str, Any]]:
    refs = item.get("source_message_refs")
    if not isinstance(refs, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        channel = str(ref.get("channel") or "").strip()
        msg_id = ref.get("id")
        if channel and msg_id is not None:
            cleaned.append({"channel": channel, "id": msg_id})
    return cleaned


def _item_title(item: dict[str, Any]) -> str:
    for key in ("topic", "company", "project", "event", "role", "title"):
        value = str(item.get(key) or "").strip()
        if value:
            return value[:160]
    refs = _source_refs(item)
    if refs:
        return f"{refs[0]['channel']}#{refs[0]['id']}"
    return "Telegram signal"


def _item_key(profile_id: str, item: dict[str, Any]) -> str:
    state = item.get("decision_state") if isinstance(item.get("decision_state"), dict) else {}
    semantic_cluster = str(state.get("semantic_cluster") or "").strip()
    if semantic_cluster:
        return semantic_cluster
    basis = {
        "profile_id": profile_id,
        "title": _item_title(item),
        "refs": _source_refs(item),
    }
    return "monitor:" + sha256_text(stable_json(basis))[:24]


def _sanitize_item(item: dict[str, Any]) -> dict[str, Any]:
    blocked = {"text", "raw_text", "message", "message_text", "body", "content"}
    sanitized = {key: value for key, value in item.items() if key not in blocked}
    sanitized["schema_version"] = "monitor_item_projection_v1"
    return sanitized


def card_id_for_item(profile_id: str, item: dict[str, Any]) -> str:
    basis = {"profile_id": profile_id, "item_key": _item_key(profile_id, item), "refs": _source_refs(item)}
    return "card_" + sha256_text(stable_json(basis))[:24]


def upsert_review_cards(
    conn: sqlite3.Connection,
    *,
    profile_id: str,
    run_id: str,
    items: Iterable[dict[str, Any]],
    report_path: str | None = None,
    dashboard_url: str | None = None,
) -> list[dict[str, Any]]:
    now = utc_now()
    cards: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        card_id = card_id_for_item(profile_id, item)
        item_key = _item_key(profile_id, item)
        title = _item_title(item)
        rating = str(item.get("rating") or "unknown")
        state = item.get("decision_state") if isinstance(item.get("decision_state"), dict) else {}
        decision_status = str(state.get("status") or "unknown")
        refs = _source_refs(item)
        existing = conn.execute(
            "SELECT status, first_run_id, created_at, handled_at FROM review_cards WHERE card_id = ?",
            (card_id,),
        ).fetchone()
        status = existing["status"] if existing else PENDING_STATUS
        first_run_id = existing["first_run_id"] if existing else run_id
        created_at = existing["created_at"] if existing else now
        handled_at = existing["handled_at"] if existing else None
        conn.execute(
            """
            INSERT OR REPLACE INTO review_cards(
                card_id, profile_id, item_key, title, rating, decision_status,
                source_refs_json, item_json, status, first_run_id, last_run_id,
                report_path, dashboard_url, created_at, updated_at, handled_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                card_id,
                profile_id,
                item_key,
                title,
                rating,
                decision_status,
                stable_json(refs),
                stable_json(_sanitize_item(item)),
                status,
                first_run_id,
                run_id,
                report_path,
                dashboard_url,
                created_at,
                now,
                handled_at,
            ),
        )
        cards.append(get_review_card(conn, card_id))
    conn.commit()
    return cards


def get_review_card(conn: sqlite3.Connection, card_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM review_cards WHERE card_id = ?", (card_id,)).fetchone()
    if not row:
        raise MonitorStateError(f"Review card not found: {card_id}")
    return _card_from_row(row)


def _card_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "schema_version": REVIEW_CARD_SCHEMA_VERSION,
        "card_id": row["card_id"],
        "profile_id": row["profile_id"],
        "item_key": row["item_key"],
        "title": row["title"],
        "rating": row["rating"],
        "decision_status": row["decision_status"],
        "source_refs": parse_json(row["source_refs_json"], []),
        "item": parse_json(row["item_json"], {}),
        "status": row["status"],
        "first_run_id": row["first_run_id"],
        "last_run_id": row["last_run_id"],
        "report_path": row["report_path"],
        "dashboard_url": row["dashboard_url"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "handled_at": row["handled_at"],
    }


def alert_candidates(cards: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for card in cards:
        item = card.get("item") if isinstance(card.get("item"), dict) else {}
        state = item.get("decision_state") if isinstance(item.get("decision_state"), dict) else {}
        if card.get("status") in HANDLED_STATUSES:
            continue
        if str(item.get("rating") or "").lower() == "high" and state.get("status") in {"new", "changed"}:
            candidates.append(card)
    return candidates


def record_alert_event(
    conn: sqlite3.Connection,
    *,
    run_id: str,
    card_id: str,
    profile_id: str,
    target_id: str,
    status: str,
    payload: dict[str, Any],
    delivery_attempt: dict[str, Any],
) -> dict[str, Any]:
    event = {
        "schema_version": ALERT_EVENT_SCHEMA_VERSION,
        "alert_id": "alert_" + uuid.uuid4().hex,
        "run_id": run_id,
        "card_id": card_id,
        "profile_id": profile_id,
        "target_id": target_id,
        "status": status,
        "payload": payload,
        "delivery_attempt": delivery_attempt,
        "created_at": utc_now(),
    }
    conn.execute(
        """
        INSERT INTO alert_events(alert_id, run_id, card_id, profile_id, target_id, status,
                                 payload_json, delivery_attempt_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event["alert_id"],
            run_id,
            card_id,
            profile_id,
            target_id,
            status,
            stable_json(payload),
            stable_json(delivery_attempt),
            event["created_at"],
        ),
    )
    conn.commit()
    return event


def set_card_action(
    conn: sqlite3.Connection,
    *,
    card_id: str,
    action: str,
    note: str = "",
    profile_path: Path | None = None,
) -> dict[str, Any]:
    if action not in REVIEW_ACTIONS:
        raise MonitorStateError(f"Unsupported review action: {action}")
    card = get_review_card(conn, card_id)
    now = utc_now()
    status = ACTION_TO_STATUS[action]
    conn.execute(
        "UPDATE review_cards SET status = ?, handled_at = ?, updated_at = ? WHERE card_id = ?",
        (status, now, now, card_id),
    )
    conn.execute(
        """
        INSERT INTO feedback_events(event_id, card_id, profile_id, action, note, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("feedback_" + uuid.uuid4().hex, card_id, card["profile_id"], action, note, now),
    )
    patch = None
    if action == "follow_up":
        patch = create_profile_patch_suggestion(
            conn,
            profile_id=card["profile_id"],
            card_id=card_id,
            note=note,
            profile_path=profile_path,
        )
    conn.commit()
    updated = get_review_card(conn, card_id)
    if patch:
        updated["profile_patch_suggestion"] = patch
    return updated


def _append_follow_up_rule(profile_text: str, note: str) -> str:
    clean_note = " ".join(note.split())
    line = f"- {clean_note}" if clean_note else "- Follow up on similar future items."
    heading = "## Follow-up Preferences"
    if heading not in profile_text:
        suffix = "\n\n" if profile_text.endswith("\n") else "\n\n"
        return f"{profile_text}{suffix}{heading}\n{line}\n"
    lines = profile_text.splitlines()
    output: list[str] = []
    inserted = False
    in_section = False
    for raw in lines:
        if raw.strip() == heading:
            in_section = True
            output.append(raw)
            continue
        if in_section and raw.startswith("## "):
            output.append(line)
            inserted = True
            in_section = False
        output.append(raw)
    if in_section and not inserted:
        output.append(line)
    return "\n".join(output).rstrip() + "\n"


def create_profile_patch_suggestion(
    conn: sqlite3.Connection,
    *,
    profile_id: str,
    card_id: str | None,
    note: str,
    profile_path: Path | None,
) -> dict[str, Any]:
    if profile_path is None:
        row = conn.execute("SELECT path FROM profiles WHERE profile_id = ?", (profile_id,)).fetchone()
        if not row:
            raise MonitorStateError(f"Profile is not registered: {profile_id}")
        profile_path = Path(row["path"])
    if not profile_path.exists():
        raise MonitorStateError(f"Profile file not found: {profile_path}")
    current = profile_path.read_text(encoding="utf-8")
    proposed = _append_follow_up_rule(current, note)
    diff = "\n".join(
        difflib.unified_diff(
            current.splitlines(),
            proposed.splitlines(),
            fromfile=str(profile_path),
            tofile=str(profile_path),
            lineterm="",
        )
    )
    now = utc_now()
    patch = {
        "schema_version": PROFILE_PATCH_SCHEMA_VERSION,
        "patch_id": "patch_" + uuid.uuid4().hex,
        "profile_id": profile_id,
        "card_id": card_id,
        "note": note,
        "status": "pending",
        "diff_text": diff,
        "proposed_profile_text": proposed,
        "created_at": now,
        "applied_at": None,
    }
    conn.execute(
        """
        INSERT INTO profile_patch_suggestions(
            patch_id, profile_id, card_id, note, status, diff_text,
            proposed_profile_text, created_at, applied_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            patch["patch_id"],
            profile_id,
            card_id,
            note,
            "pending",
            diff,
            proposed,
            now,
            None,
        ),
    )
    return patch


def apply_profile_patch(conn: sqlite3.Connection, *, patch_id: str, profile_path: Path | None = None) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM profile_patch_suggestions WHERE patch_id = ?",
        (patch_id,),
    ).fetchone()
    if not row:
        raise MonitorStateError(f"Profile patch not found: {patch_id}")
    if row["status"] != "pending":
        raise MonitorStateError(f"Profile patch is not pending: {patch_id}")
    if profile_path is None:
        profile_row = conn.execute("SELECT path FROM profiles WHERE profile_id = ?", (row["profile_id"],)).fetchone()
        if not profile_row:
            raise MonitorStateError(f"Profile is not registered: {row['profile_id']}")
        profile_path = Path(profile_row["path"])
    current = profile_path.read_text(encoding="utf-8") if profile_path.exists() else ""
    snapshot_id = "snapshot_" + uuid.uuid4().hex
    now = utc_now()
    conn.execute(
        """
        INSERT INTO profile_snapshots(snapshot_id, profile_id, profile_path, profile_hash,
                                      profile_text, reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (snapshot_id, row["profile_id"], str(profile_path), sha256_text(current), current, f"before {patch_id}", now),
    )
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    profile_path.write_text(row["proposed_profile_text"], encoding="utf-8")
    conn.execute(
        "UPDATE profile_patch_suggestions SET status = ?, applied_at = ? WHERE patch_id = ?",
        ("applied", now, patch_id),
    )
    conn.commit()
    return {
        "patch_id": patch_id,
        "profile_id": row["profile_id"],
        "status": "applied",
        "snapshot_id": snapshot_id,
        "profile_path": str(profile_path),
        "applied_at": now,
    }


def dashboard_snapshot(conn: sqlite3.Connection) -> dict[str, Any]:
    profiles = [
        {
            "profile_id": row["profile_id"],
            "path": row["path"],
            "enabled": bool(row["enabled"]),
            "config": parse_json(row["config_json"], {}),
            "updated_at": row["updated_at"],
        }
        for row in conn.execute("SELECT * FROM profiles ORDER BY profile_id").fetchall()
    ]
    inbox = [
        _card_from_row(row)
        for row in conn.execute(
            "SELECT * FROM review_cards WHERE status = ? ORDER BY updated_at DESC LIMIT 200",
            (PENDING_STATUS,),
        ).fetchall()
    ]
    runs = [
        {
            "run_id": row["run_id"],
            "profile_id": row["profile_id"],
            "status": row["status"],
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "manifest": parse_json(row["manifest_json"], {}),
        }
        for row in conn.execute("SELECT * FROM runs ORDER BY started_at DESC LIMIT 100").fetchall()
    ]
    delivery_targets = [
        {
            "schema_version": DELIVERY_TARGET_SCHEMA_VERSION,
            "target_id": row["target_id"],
            "type": row["target_type"],
            "enabled": bool(row["enabled"]),
            "config": parse_json(row["config_json"], {}),
            "updated_at": row["updated_at"],
        }
        for row in conn.execute("SELECT * FROM delivery_targets ORDER BY target_id").fetchall()
    ]
    patches = [
        {
            "schema_version": PROFILE_PATCH_SCHEMA_VERSION,
            "patch_id": row["patch_id"],
            "profile_id": row["profile_id"],
            "card_id": row["card_id"],
            "note": row["note"],
            "status": row["status"],
            "diff_text": row["diff_text"],
            "created_at": row["created_at"],
            "applied_at": row["applied_at"],
        }
        for row in conn.execute(
            "SELECT * FROM profile_patch_suggestions ORDER BY created_at DESC LIMIT 100"
        ).fetchall()
    ]
    return {
        "schema_version": "dashboard_state_v1",
        "profiles": profiles,
        "inbox": inbox,
        "runs": runs,
        "delivery_targets": delivery_targets,
        "profile_patch_suggestions": patches,
    }
