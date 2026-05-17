"""Signal Desk local server selection and health helpers."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import socket
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib import error as urllib_error
from urllib.parse import urlparse
from urllib.request import urlopen

DESK_HEALTH_SCHEMA_VERSION = "desk_health_v1"
DESK_APP_ID = "tgcs-signal-desk"
DESK_VERSION = "0.5.0-alpha.1"
DESK_AUTO_PORT_END = 8799
LOOPBACK_DASHBOARD_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _runtime_code_fingerprint(*, scripts_dir: Path | None = None) -> str:
    root = scripts_dir or Path(__file__).resolve().parent
    digest = hashlib.sha256()
    paths = sorted(path for path in root.glob("*.py") if path.is_file())
    if not paths:
        digest.update(b"no-python-sources")
    for path in paths:
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            relative = path.name
        digest.update(relative.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        try:
            digest.update(path.read_bytes())
        except OSError:
            digest.update(b"unreadable")
        digest.update(b"\0")
    return digest.hexdigest()


DESK_RUNTIME_CODE_FINGERPRINT = _runtime_code_fingerprint()


@dataclass(frozen=True)
class DashboardServerSelection:
    url: str
    port: int
    server: ThreadingHTTPServer | None
    reused_existing: bool = False


def dashboard_host_warning(host: str) -> str | None:
    normalized = host.strip().lower()
    if normalized in LOOPBACK_DASHBOARD_HOSTS:
        return None
    return (
        "Dashboard host is not loopback. Dashboard state can include local workflow context "
        "and report artifacts may include raw context; only bind this server to a trusted interface."
    )


def browser_host(host: str) -> str:
    normalized = str(host or "").strip()
    if normalized in {"", "0.0.0.0"}:
        return "127.0.0.1"
    if normalized == "::":
        return "::1"
    return normalized


def dashboard_url(host: str, port: int) -> str:
    browser = browser_host(host)
    if ":" in browser and not browser.startswith("["):
        browser = f"[{browser}]"
    return f"http://{browser}:{port}"


def desk_health(*, host: str, port: int) -> dict[str, Any]:
    return {
        "schema_version": DESK_HEALTH_SCHEMA_VERSION,
        "app": DESK_APP_ID,
        "version": DESK_VERSION,
        "code_fingerprint": DESK_RUNTIME_CODE_FINGERPRINT,
        "ok": True,
        "url": dashboard_url(host, port),
        "capabilities": [
            "desk_actions_v1",
            "desk_telegram_setup_v1",
            "desk_notification_token_v1",
            "desk_ai_settings_v1",
            "desk_sources_v1",
            "desk_source_assistant_v1",
            "desk_scheduler_v1",
            "desk_bot_gateway_status_v1",
            "desk_support_status_v1",
            "dashboard_state_v1",
        ],
    }


def fetch_compatible_desk_health(
    host: str,
    port: int,
    *,
    timeout_seconds: float = 0.25,
    socket_module=socket,
    urlopen_fn: Callable[..., Any] = urlopen,
    dashboard_url_fn: Callable[[str, int], str] = dashboard_url,
    browser_host_fn: Callable[[str], str] = browser_host,
    is_loopback_address_fn: Callable[[object], bool] | None = None,
) -> dict[str, Any] | None:
    is_loopback = is_loopback_address_fn or is_loopback_address
    try:
        with socket_module.create_connection((browser_host_fn(host), port), timeout=0.15):
            pass
    except OSError:
        return None
    try:
        with urlopen_fn(f"{dashboard_url_fn(host, port)}/api/desk/health", timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib_error.URLError, TimeoutError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != DESK_HEALTH_SCHEMA_VERSION:
        return None
    if payload.get("app") != DESK_APP_ID:
        return None
    if payload.get("code_fingerprint") != DESK_RUNTIME_CODE_FINGERPRINT:
        return None
    health_url = str(payload.get("url") or "").strip()
    if health_url:
        parsed = urlparse(health_url)
        if parsed.scheme != "http" or not parsed.hostname or not is_loopback(parsed.hostname) or parsed.port != port:
            return None
    return payload


def is_tcp_port_listening(
    host: str,
    port: int,
    *,
    timeout_seconds: float = 0.15,
    socket_module=socket,
    browser_host_fn: Callable[[str], str] = browser_host,
) -> bool:
    try:
        with socket_module.create_connection((browser_host_fn(host), port), timeout=timeout_seconds):
            return True
    except OSError:
        return False


def select_dashboard_server(
    *,
    host: str,
    port: int,
    auto_port: bool,
    handler_cls: type[BaseHTTPRequestHandler],
    server_cls: type[ThreadingHTTPServer] = ThreadingHTTPServer,
    fetch_health_fn: Callable[[str, int], dict[str, Any] | None] = fetch_compatible_desk_health,
    is_port_listening_fn: Callable[[str, int], bool] = is_tcp_port_listening,
    reuse_existing: bool = True,
) -> DashboardServerSelection:
    ports = [port]
    if auto_port:
        ports.extend(range(port + 1, DESK_AUTO_PORT_END + 1))
    last_error: OSError | None = None
    for candidate in ports:
        if auto_port:
            health = fetch_health_fn(host, candidate)
            if health and reuse_existing:
                return DashboardServerSelection(
                    url=dashboard_url(host, candidate),
                    port=candidate,
                    server=None,
                    reused_existing=True,
                )
            if is_port_listening_fn(host, candidate):
                # Windows can allow a second bind when an older local tool did
                # not claim the port exclusively. Skip that URL so the browser
                # cannot land on an unrelated directory listing or test server.
                last_error = OSError(f"Port {candidate} is already used by another local service.")
                continue
        elif is_port_listening_fn(host, candidate):
            raise OSError(f"Port {candidate} is already used by another local service.")
        try:
            server = server_cls((host, candidate), handler_cls)
            return DashboardServerSelection(
                url=dashboard_url(host, candidate),
                port=candidate,
                server=server,
            )
        except OSError as exc:
            last_error = exc
            if not auto_port:
                raise
    raise OSError(f"No available Signal Desk port in {port}-{DESK_AUTO_PORT_END}.") from last_error


def is_loopback_address(value: object) -> bool:
    text = str(value or "").strip().strip("[]")
    if not text:
        return False
    if text.casefold() == "localhost":
        return True
    if text.startswith("::ffff:"):
        text = text.removeprefix("::ffff:")
    try:
        return ipaddress.ip_address(text).is_loopback
    except ValueError:
        return False
