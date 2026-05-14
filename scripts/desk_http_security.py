"""HTTP request integrity checks for Signal Desk."""

from __future__ import annotations

from typing import Any, Callable
from urllib.parse import urlparse


def request_host_port(*, headers: Any, server: Any) -> int | None:
    host = str(headers.get("Host") or "").strip() if headers is not None else ""
    if host:
        try:
            parsed = urlparse(f"//{host}")
            if parsed.port is not None:
                return parsed.port
        except ValueError:
            return None
    address = getattr(server, "server_address", None)
    if isinstance(address, tuple) and len(address) >= 2:
        try:
            return int(address[1])
        except (TypeError, ValueError):
            return None
    return None


def is_loopback_same_port_url(
    value: str,
    *,
    request_port: int | None,
    is_loopback_address_fn: Callable[[object], bool],
) -> bool:
    try:
        parsed = urlparse(value)
        source_port = parsed.port or (80 if parsed.scheme == "http" else 443 if parsed.scheme == "https" else None)
    except ValueError:
        return False
    if parsed.scheme != "http" or not parsed.hostname or not is_loopback_address_fn(parsed.hostname):
        return False
    return request_port is None or source_port == request_port


def require_post_request_integrity(
    *,
    headers: Any,
    server: Any,
    is_loopback_address_fn: Callable[[object], bool],
) -> None:
    if headers is None:
        return
    content_type = str(headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise ValueError("Signal Desk POST requests require application/json.")
    request_port = request_host_port(headers=headers, server=server)
    for header_name in ("Origin", "Referer"):
        header_value = str(headers.get(header_name) or "").strip()
        if header_value and not is_loopback_same_port_url(
            header_value,
            request_port=request_port,
            is_loopback_address_fn=is_loopback_address_fn,
        ):
            raise ValueError("Signal Desk POST requests must originate from the local dashboard.")


def require_loopback_access(
    *,
    client_address: Any,
    feature: str,
    is_loopback_address_fn: Callable[[object], bool],
) -> None:
    client_host = client_address[0] if isinstance(client_address, tuple) and client_address else "127.0.0.1"
    if is_loopback_address_fn(client_host):
        return
    raise ValueError(f"{feature} requires opening Signal Desk from localhost.")
