"""HTTP routes for the Telegram Mini App companion review surface."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from http import HTTPStatus
from typing import Any
from urllib.parse import unquote

from scripts import desk_miniapp


MINIAPP_ACTION_ALLOWED_FIELDS = {"action", "note"}
MINIAPP_SOURCE_ALLOWED_FIELDS = {"topic"}
MINIAPP_NOTE_MAX_LENGTH = 1000
MINIAPP_ALLOWED_REVIEW_ACTIONS = {
    "applied",
    "contacted",
    "saved",
    "dismissed",
    "duplicate",
    "reopen",
    "keep",
    "skip",
    "false_positive",
    "follow_up",
    "undo_decision",
}


def handle_miniapp_get_route(
    handler: Any,
    path: str,
    *,
    authorize_request: Callable[[Any], dict],
    close_after_use: Callable[[Any], Any],
    miniapp_state: Callable[..., dict],
) -> bool:
    if path != "/api/miniapp/state":
        return False
    auth = authorize_request(handler)
    with close_after_use(handler._connect()) as conn:
        payload = miniapp_state(conn, auth=auth)
    handler._json(HTTPStatus.OK, {"ok": True, "miniapp": payload})
    return True


def is_miniapp_post_route(path: str) -> bool:
    return path == "/api/miniapp/sources/starter" or (
        path.startswith("/api/miniapp/review-cards/") and path.endswith("/action")
    )


def handle_miniapp_post_route(
    handler: Any,
    path: str,
    body: Mapping[str, Any],
    *,
    authorize_request: Callable[[Any], dict],
    close_after_use: Callable[[Any], Any],
    monitor_state_module: Any,
    import_starter_sources: Callable[[dict], dict] | None = None,
) -> bool:
    if not is_miniapp_post_route(path):
        return False
    if path == "/api/miniapp/sources/starter":
        _reject_unexpected_source_fields(body)
        authorize_request(handler)
        if import_starter_sources is None:
            raise ValueError("Mini App source import is unavailable.")
        topic = str(body.get("topic") or "jobs").strip() or "jobs"
        result = import_starter_sources({"topic": topic})
        handler._json(HTTPStatus.OK, {"ok": True, "result": result})
        return True
    _reject_unexpected_fields(body)
    auth = authorize_request(handler)
    card_id = unquote(path.removeprefix("/api/miniapp/review-cards/").removesuffix("/action").strip("/"))
    action = str(body.get("action") or "").strip()
    note = " ".join(str(body.get("note") or "").split())
    if action not in MINIAPP_ALLOWED_REVIEW_ACTIONS:
        raise ValueError(f"Unsupported Mini App review action: {action or 'empty'}")
    if len(note) > MINIAPP_NOTE_MAX_LENGTH:
        raise ValueError("Mini App review note is too long.")
    with close_after_use(handler._connect()) as conn:
        if action == "undo_decision":
            raw_card = monitor_state_module.undo_card_action(conn, card_id=card_id)
        else:
            raw_card = monitor_state_module.set_card_action(conn, card_id=card_id, action=action, note=note)
    card = desk_miniapp.miniapp_card(
        raw_card,
        include_report_path=auth.get("source") == "loopback_preview" and not auth.get("miniapp_only"),
    )
    handler._json(HTTPStatus.OK, {"ok": True, "card": card})
    return True


def _reject_unexpected_fields(body: Mapping[str, Any]) -> None:
    unexpected = sorted(set(body) - MINIAPP_ACTION_ALLOWED_FIELDS)
    if unexpected:
        raise ValueError(f"Unexpected Mini App review field: {unexpected[0]}")


def _reject_unexpected_source_fields(body: Mapping[str, Any]) -> None:
    unexpected = sorted(set(body) - MINIAPP_SOURCE_ALLOWED_FIELDS)
    if unexpected:
        raise ValueError(f"Unexpected Mini App source field: {unexpected[0]}")
