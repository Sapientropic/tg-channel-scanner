"""POST route dispatch for local Signal Desk profile mutations."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Set
from http import HTTPStatus
from typing import Any


def handle_profile_post_route(
    handler: Any,
    path: str,
    body: Mapping[str, Any],
    *,
    require_loopback_access: Callable[[Any, str], None],
    close_after_use: Callable[[Any], Any],
    monitor_state_module: Any,
    profile_routes_module: Any,
    create_profile_from_brief: Callable[[Any, Mapping[str, Any]], dict],
    profile_enabled_allowed_fields: Set[str],
    profile_runtime_settings_allowed_fields: Set[str],
    profile_draft_note_allowed_fields: Set[str],
    profile_draft_note_max_length: int,
    profile_matching_preferences_allowed_fields: Set[str],
    profile_matching_preferences_max_length: int,
    delete_profile: Callable[[Any, str], dict] | None = None,
) -> bool:
    if path == "/api/profiles/create":
        require_loopback_access(handler, "Profile creation")
        with close_after_use(handler._connect()) as conn:
            result = create_profile_from_brief(conn, body)
        handler._json(HTTPStatus.OK, {"ok": True, "profile": result})
        return True
    if path.startswith("/api/profiles/") and path.endswith("/alert-mode"):
        require_loopback_access(handler, "Profile settings")
        with close_after_use(handler._connect()) as conn:
            payload = profile_routes_module.profile_alert_mode_payload(
                conn,
                path=path,
                body=body,
                monitor_state_module=monitor_state_module,
            )
        handler._json(HTTPStatus.OK, payload)
        return True
    if path.startswith("/api/profiles/") and path.endswith("/enabled"):
        require_loopback_access(handler, "Profile settings")
        # These request-shape gates must stay before state access. They keep
        # malformed or private profile text from touching local dashboard state.
        profile_routes_module.validate_profile_enabled_body(body, allowed_fields=profile_enabled_allowed_fields)
        with close_after_use(handler._connect()) as conn:
            payload = profile_routes_module.profile_enabled_payload(
                conn,
                path=path,
                body=body,
                monitor_state_module=monitor_state_module,
                allowed_fields=profile_enabled_allowed_fields,
            )
        handler._json(HTTPStatus.OK, payload)
        return True
    if path.startswith("/api/profiles/") and path.endswith("/runtime-settings"):
        require_loopback_access(handler, "Profile settings")
        profile_routes_module.validate_profile_runtime_settings_body(
            body,
            allowed_fields=profile_runtime_settings_allowed_fields,
        )
        with close_after_use(handler._connect()) as conn:
            payload = profile_routes_module.profile_runtime_settings_payload(
                conn,
                path=path,
                body=body,
                monitor_state_module=monitor_state_module,
                allowed_fields=profile_runtime_settings_allowed_fields,
            )
        handler._json(HTTPStatus.OK, payload)
        return True
    if path.startswith("/api/profiles/") and path.endswith("/delete"):
        require_loopback_access(handler, "Profile deletion")
        profile_routes_module.validate_profile_delete_body(body)
        if delete_profile is None:
            raise ValueError("Profile deletion is not available.")
        with close_after_use(handler._connect()) as conn:
            payload = profile_routes_module.profile_delete_payload(
                conn,
                path=path,
                body=body,
                delete_profile=delete_profile,
            )
        handler._json(HTTPStatus.OK, payload)
        return True
    if path.startswith("/api/profiles/") and path.endswith("/draft-note"):
        require_loopback_access(handler, "Profile draft note")
        profile_routes_module.validate_profile_draft_note_text(
            body,
            monitor_state_module=monitor_state_module,
            allowed_fields=profile_draft_note_allowed_fields,
            max_length=profile_draft_note_max_length,
        )
        with close_after_use(handler._connect()) as conn:
            payload = profile_routes_module.profile_draft_note_payload(
                conn,
                path=path,
                body=body,
                monitor_state_module=monitor_state_module,
                allowed_fields=profile_draft_note_allowed_fields,
                max_length=profile_draft_note_max_length,
            )
        handler._json(HTTPStatus.OK, payload)
        return True
    if path.startswith("/api/profiles/") and path.endswith("/matching-preferences"):
        require_loopback_access(handler, "Profile matching preferences")
        profile_routes_module.validate_profile_matching_preferences_text(
            body,
            monitor_state_module=monitor_state_module,
            allowed_fields=profile_matching_preferences_allowed_fields,
            max_length=profile_matching_preferences_max_length,
        )
        with close_after_use(handler._connect()) as conn:
            payload = profile_routes_module.profile_matching_preferences_payload(
                conn,
                path=path,
                body=body,
                monitor_state_module=monitor_state_module,
                allowed_fields=profile_matching_preferences_allowed_fields,
                max_length=profile_matching_preferences_max_length,
            )
        handler._json(HTTPStatus.OK, payload)
        return True
    for action in ("apply", "revert", "replay"):
        if path.startswith("/api/profile-patches/") and path.endswith(f"/{action}"):
            require_loopback_access(handler, "Profile patch actions")
            with close_after_use(handler._connect()) as conn:
                payload = profile_routes_module.profile_patch_action_payload(
                    conn,
                    path=path,
                    action=action,
                    monitor_state_module=monitor_state_module,
                )
            handler._json(HTTPStatus.OK, payload)
            return True
    return False
