"""GET route dispatch for the local Signal Desk HTTP facade."""

from __future__ import annotations

from collections.abc import Callable
from http import HTTPStatus
from typing import Any


def handle_get_route(
    handler: Any,
    path: str,
    *,
    require_loopback_access: Callable[[Any, str], None],
    close_after_use: Callable[[Any], Any],
    desk_health: Callable[..., dict],
    desk_actions: Callable[[], dict],
    telegram_status: Callable[[], dict],
    desk_sources: Callable[[], dict],
    desk_scheduler_status: Callable[[], dict],
    desk_notification_token_status: Callable[[], dict],
    desk_bot_gateway_status: Callable[[Any], dict],
    desk_ai_settings_status: Callable[[], dict],
    dashboard_state_payload: Callable[[Any], dict],
    desk_support_status: Callable[..., dict] | None = None,
    profile_template_catalog: Callable[[], dict] | None = None,
) -> bool:
    if path == "/api/desk/health":
        require_loopback_access(handler, "Signal Desk health")
        server_host, server_port = handler.server.server_address[:2]
        handler._json(HTTPStatus.OK, desk_health(host=str(server_host), port=int(server_port)))
        return True
    if path == "/api/desk/actions":
        handler._json(HTTPStatus.OK, desk_actions())
        return True
    if path == "/api/desk/telegram-status":
        require_loopback_access(handler, "Telegram setup")
        handler._json(HTTPStatus.OK, {"ok": True, "telegram": telegram_status()})
        return True
    if path == "/api/desk/sources":
        require_loopback_access(handler, "Source library")
        handler._json(HTTPStatus.OK, {"ok": True, "sources": desk_sources()})
        return True
    if path == "/api/desk/scheduler-status":
        require_loopback_access(handler, "Scheduler status")
        handler._json(HTTPStatus.OK, {"ok": True, "scheduler": desk_scheduler_status()})
        return True
    if path == "/api/desk/notification-token/status":
        require_loopback_access(handler, "Notification token status")
        handler._json(HTTPStatus.OK, {"ok": True, "token": desk_notification_token_status()})
        return True
    if path == "/api/desk/bot-gateway-status":
        require_loopback_access(handler, "Bot gateway status")
        with close_after_use(handler._connect()) as conn:
            handler._json(HTTPStatus.OK, {"ok": True, "bot_gateway": desk_bot_gateway_status(conn)})
        return True
    if path == "/api/desk/ai-settings/status":
        require_loopback_access(handler, "AI API settings status")
        handler._json(HTTPStatus.OK, {"ok": True, "ai": desk_ai_settings_status()})
        return True
    if path == "/api/desk/support-status":
        require_loopback_access(handler, "Support diagnostics")
        if desk_support_status is None:
            raise ValueError("Support diagnostics are not available.")
        server_host, server_port = handler.server.server_address[:2]
        handler._json(
            HTTPStatus.OK,
            {
                "ok": True,
                "support": desk_support_status(
                    host=str(server_host),
                    port=int(server_port),
                    db_path=handler.db_path,
                ),
            },
        )
        return True
    if path == "/api/profiles/templates":
        require_loopback_access(handler, "Profile templates")
        if profile_template_catalog is None:
            raise ValueError("Profile template catalog is not available.")
        handler._json(HTTPStatus.OK, {"ok": True, "templates": profile_template_catalog()})
        return True
    if path == "/api/state":
        require_loopback_access(handler, "Dashboard state")
        with close_after_use(handler._connect()) as conn:
            handler._json(HTTPStatus.OK, dashboard_state_payload(conn))
        return True
    if path.startswith("/artifacts/"):
        require_loopback_access(handler, "Report artifacts")
        handler._serve_artifact(path.removeprefix("/artifacts/"))
        return True
    return False
