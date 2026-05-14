"""POST route dispatch for local Signal Desk source library mutations."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from http import HTTPStatus
from typing import Any
from urllib.parse import unquote


def handle_source_post_route(
    handler: Any,
    path: str,
    body: Mapping[str, Any],
    *,
    require_loopback_access: Callable[[Any, str], None],
    preview_desk_source_import: Callable[[Mapping[str, Any]], dict],
    import_desk_sources: Callable[[Mapping[str, Any]], dict],
    import_starter_sources: Callable[[Mapping[str, Any]], dict],
    run_source_assistant: Callable[[Mapping[str, Any]], dict],
    set_desk_source_enabled: Callable[[str, Mapping[str, Any]], dict],
    set_desk_source_topics: Callable[[str, Mapping[str, Any]], dict],
    remove_desk_source: Callable[[str, Mapping[str, Any]], dict],
) -> bool:
    if path == "/api/desk/sources/preview":
        require_loopback_access(handler, "Source import")
        handler._json(HTTPStatus.OK, {"ok": True, "result": preview_desk_source_import(body)})
        return True
    if path == "/api/desk/sources/import":
        require_loopback_access(handler, "Source import")
        handler._json(HTTPStatus.OK, {"ok": True, "result": import_desk_sources(body)})
        return True
    if path == "/api/desk/sources/starter":
        require_loopback_access(handler, "Starter source import")
        handler._json(HTTPStatus.OK, {"ok": True, "result": import_starter_sources(body)})
        return True
    if path == "/api/desk/sources/assistant":
        require_loopback_access(handler, "Source assistant")
        handler._json(HTTPStatus.OK, {"ok": True, "result": run_source_assistant(body)})
        return True
    if path.startswith("/api/desk/sources/") and path.endswith("/enabled"):
        require_loopback_access(handler, "Source library")
        source_id = unquote(path.removeprefix("/api/desk/sources/").removesuffix("/enabled").strip("/"))
        handler._json(HTTPStatus.OK, {"ok": True, "sources": set_desk_source_enabled(source_id, body)})
        return True
    if path.startswith("/api/desk/sources/") and path.endswith("/topics"):
        require_loopback_access(handler, "Source library")
        source_id = unquote(path.removeprefix("/api/desk/sources/").removesuffix("/topics").strip("/"))
        handler._json(HTTPStatus.OK, {"ok": True, "sources": set_desk_source_topics(source_id, body)})
        return True
    if path.startswith("/api/desk/sources/") and path.endswith("/remove"):
        require_loopback_access(handler, "Source library")
        source_id = unquote(path.removeprefix("/api/desk/sources/").removesuffix("/remove").strip("/"))
        handler._json(HTTPStatus.OK, {"ok": True, "sources": remove_desk_source(source_id, body)})
        return True
    return False
