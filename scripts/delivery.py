"""Delivery adapters for v0.5-alpha monitor alerts.

This module deliberately keeps outbound delivery separate from monitor state.
The monitor can dry-run delivery in tests and CI, while live Telegram Bot API
calls must be explicitly selected by the caller.  Bot tokens are resolved from
the environment first, then from the local OS credential store when available.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from scripts.item_display import display_item_title
from scripts import local_credentials


TELEGRAM_BOT_TOKEN_ENV = "TGCS_TELEGRAM_BOT_TOKEN"
TELEGRAM_BOT_TOKEN_CREDENTIAL_TARGET = "tgcs.signal-desk.telegram-bot-token"
BOT_TOKEN_RE = re.compile(r"\b\d{5,12}:[A-Za-z0-9_-]{10,}\b")
PROVIDER_KEY_RE = re.compile(r"\b(?:sk|sk-proj|sk-ant|ak)-[A-Za-z0-9_-]{12,}\b", re.IGNORECASE)
AUTHORIZATION_RE = re.compile(r"(?i)\bAuthorization\s*:\s*Bearer\s+[A-Za-z0-9._~+/=-]{8,}")
ENV_SECRET_RE = re.compile(r"(?i)\b[A-Z0-9_]*(?:API[_-]?KEY|TOKEN|SECRET|PASSWORD)\b\s*=\s*(?:\"[^\"\r\n]+\"|'[^'\r\n]+'|[^\s`'\"]+)")
KEY_VALUE_SECRET_RE = re.compile(r"(?i)\b(?:api[_-]?key|token|secret|password)\b\s*[:=]\s*(?:\"[^\"\r\n]+\"|'[^'\r\n]+'|[^\s`'\"]+)")
ARGV_DUMP_RE = re.compile(r"(?i)\b(?:argv|args)\b\s*(?::|=)?\s*\[[^\]]*\]|\b(?:argv|args)\b\s*[:=]\s*[^\r\n]+")
WINDOWS_PATH_RE = re.compile(r"[A-Za-z]:\\[^\s`'\"]+")
UNC_PATH_RE = re.compile(r"\\\\[^\\\s]+\\[^\s`'\"]+")
POSIX_PRIVATE_PATH_RE = re.compile(r"(?<!\w)/(?:home|Users|users|var|tmp|etc|private/tmp)/[^\s`'\"]+")
CHAT_ID_FIELD_RE = re.compile(r"\bchat[_ -]?id\b\s*[:=]?\s*-?\d{5,20}\b", re.IGNORECASE)
BARE_CHAT_ID_RE = re.compile(r"(?<![\w:])-?\d{8,20}(?!\w)")


def redact_delivery_error(value: object) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    text = BOT_TOKEN_RE.sub("[redacted-token]", text)
    text = PROVIDER_KEY_RE.sub("[redacted-key]", text)
    text = AUTHORIZATION_RE.sub("Authorization: Bearer [redacted-key]", text)
    text = ENV_SECRET_RE.sub(lambda match: f"{match.group(0).split('=')[0].strip()}=[redacted-secret]", text)
    text = KEY_VALUE_SECRET_RE.sub(lambda match: re.split(r"[:=]", match.group(0), maxsplit=1)[0].strip() + "=[redacted-secret]", text)
    text = ARGV_DUMP_RE.sub("argv=[redacted-argv]", text)
    text = WINDOWS_PATH_RE.sub("[redacted-path]", text)
    text = UNC_PATH_RE.sub("[redacted-path]", text)
    text = POSIX_PRIVATE_PATH_RE.sub("[redacted-path]", text)
    text = CHAT_ID_FIELD_RE.sub("chat_id [redacted-chat-id]", text)
    text = BARE_CHAT_ID_RE.sub("[redacted-chat-id]", text)
    return _clean_text(text, max_len=500)


class DeliveryError(Exception):
    """Raised when a delivery adapter cannot complete a requested live send."""


@dataclass(frozen=True)
class DeliveryAttempt:
    target_id: str
    target_type: str
    mode: str
    ok: bool
    status: str
    message_id: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        error = redact_delivery_error(self.error) if self.error else None
        return {
            "target_id": self.target_id,
            "target_type": self.target_type,
            "mode": self.mode,
            "ok": self.ok,
            "status": self.status,
            "message_id": self.message_id,
            "error": error,
        }


@dataclass(frozen=True)
class TelegramBotToken:
    token: str
    source: str
    updated_at: str | None = None


def resolve_telegram_bot_token(
    *,
    token_env: str = TELEGRAM_BOT_TOKEN_ENV,
    credential_target: str = TELEGRAM_BOT_TOKEN_CREDENTIAL_TARGET,
) -> TelegramBotToken:
    env_token = os.environ.get(token_env, "").strip()
    if env_token:
        return TelegramBotToken(token=env_token, source="environment")
    if not local_credentials.is_supported():
        return TelegramBotToken(token="", source="missing")
    try:
        stored = local_credentials.read_secret(credential_target)
    except local_credentials.CredentialStoreError:
        return TelegramBotToken(token="", source="credential_error")
    if stored and stored.secret.strip():
        return TelegramBotToken(
            token=stored.secret.strip(),
            source=local_credentials.backend(),
            updated_at=stored.updated_at,
        )
    return TelegramBotToken(token="", source="missing")


def _clean_text(value: object, *, max_len: int = 240) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "..."


def _item_title(item: dict[str, Any]) -> str:
    return display_item_title(item, fallback="Telegram signal", max_len=120)


def _source_ref_label(ref: dict[str, Any]) -> str:
    channel = _clean_text(ref.get("channel"), max_len=80)
    msg_id = _clean_text(ref.get("id"), max_len=40)
    if channel and msg_id:
        return f"{channel} message {msg_id}"
    if channel:
        return channel
    return ""


def _source_ref_url(ref: dict[str, Any]) -> str:
    explicit = _public_telegram_link(ref.get("url"))
    if explicit and (urlparse(explicit).hostname or "").casefold() == "t.me":
        return explicit
    try:
        from scripts.review_cards import telegram_source_ref_url
    except ModuleNotFoundError:
        return ""
    return telegram_source_ref_url(
        channel=str(ref.get("channel") or ""),
        message_id=ref.get("id"),
        source_info={},
    )


def _source_ref_candidates(*, item: dict[str, Any], card: dict[str, Any] | None) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for raw_refs in ((card or {}).get("source_refs"), item.get("source_message_refs")):
        if not isinstance(raw_refs, list):
            continue
        for ref in raw_refs:
            if isinstance(ref, dict):
                refs.append(ref)
    return refs


def _source_summary(*, item: dict[str, Any], card: dict[str, Any] | None) -> tuple[str, list[str]]:
    rendered = []
    links = []
    refs = _source_ref_candidates(item=item, card=card)
    seen_links: set[str] = set()
    for ref in refs[:5]:
        label = _source_ref_label(ref)
        if label:
            rendered.append(label)
        link = _source_ref_url(ref)
        if link and link not in seen_links:
            seen_links.add(link)
            links.append(link)
    if len(refs) > 5:
        rendered.append(f"+{len(refs) - 5} more")
    return ", ".join(rendered) if rendered else "source unavailable", links


def _telegram_markdown_escape(value: object) -> str:
    text = _clean_text(value, max_len=1000)
    for char in ("\\", "_", "*", "`", "["):
        text = text.replace(char, "\\" + char)
    return text


def _public_telegram_link(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    if parsed.scheme not in {"http", "https"}:
        return ""
    host = (parsed.hostname or "").casefold()
    if host in {"localhost", "127.0.0.1", "::1"}:
        return ""
    return text


def build_telegram_alert_text(
    *,
    item: dict[str, Any],
    card: dict[str, Any] | None = None,
    report_url: str | None = None,
    dashboard_url: str | None = None,
    actions_available: bool = False,
) -> str:
    """Build a redacted Telegram alert body.

    The alert intentionally excludes raw Telegram message text.  It carries
    enough provenance and a compact reason to decide on the phone. Local-only
    report paths or loopback dashboard URLs are omitted because they are not
    useful inside Telegram notifications.
    """

    state = item.get("decision_state") if isinstance(item.get("decision_state"), dict) else {}
    status = _clean_text(state.get("status") or "new", max_len=40)
    rating = _clean_text(item.get("rating") or "unknown", max_len=40)
    why = _clean_text(item.get("why") or item.get("market_impact") or "", max_len=320)
    source_label, source_links = _source_summary(item=item, card=card)

    lines = [
        f"*T-Sense alert*: {_telegram_markdown_escape(_item_title(item))}",
        f"*Priority*: {_telegram_markdown_escape(rating.title())} · {_telegram_markdown_escape(status.replace('_', ' ').title())}",
    ]
    if why:
        lines.append(f"*Why*: {_telegram_markdown_escape(why)}")
    if source_links:
        lines.append(f"*Open original*: {source_links[0]}")
        if len(source_links) > 1:
            lines.append(f"*More originals*: {', '.join(source_links[1:3])}")
    else:
        lines.append(f"*Original*: {_telegram_markdown_escape(source_label)}")
    if actions_available:
        lines.append("*Action*: Buttons below update Review in Signal Desk.")
    else:
        lines.append("*Action*: Open Review in Signal Desk to mark Applied, Saved, or Not a fit.")
    public_report = _public_telegram_link(report_url)
    public_dashboard = _public_telegram_link(dashboard_url)
    if public_report:
        lines.append(f"*Report*: {public_report}")
    if public_dashboard:
        lines.append(f"*Dashboard*: {public_dashboard}")
    return "\n".join(lines)


def send_telegram_bot_message(
    *,
    target_id: str,
    chat_id: str,
    text: str,
    mode: str = "dry-run",
    token_env: str = TELEGRAM_BOT_TOKEN_ENV,
    timeout_seconds: int = 15,
    reply_markup: dict[str, Any] | None = None,
    parse_mode: str | None = "Markdown",
) -> DeliveryAttempt:
    if mode not in {"dry-run", "live"}:
        raise ValueError("mode must be dry-run or live")
    if not chat_id:
        return DeliveryAttempt(
            target_id=target_id,
            target_type="telegram_bot",
            mode=mode,
            ok=False,
            status="chat_id_missing",
            error="Telegram bot chat_id is missing.",
        )
    if mode == "dry-run":
        return DeliveryAttempt(
            target_id=target_id,
            target_type="telegram_bot",
            mode=mode,
            ok=True,
            status="dry_run",
        )

    token_status = resolve_telegram_bot_token(token_env=token_env)
    if not token_status.token:
        return DeliveryAttempt(
            target_id=target_id,
            target_type="telegram_bot",
            mode=mode,
            ok=False,
            status="token_missing",
            error=f"Telegram bot token is not configured. Save it in Signal Desk Settings or set {token_env}.",
        )

    url = f"https://api.telegram.org/bot{token_status.token}/sendMessage"
    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return DeliveryAttempt(
            target_id=target_id,
            target_type="telegram_bot",
            mode=mode,
            ok=False,
            status="request_failed",
            error=str(exc),
        )
    except json.JSONDecodeError as exc:
        return DeliveryAttempt(
            target_id=target_id,
            target_type="telegram_bot",
            mode=mode,
            ok=False,
            status="invalid_response",
            error=str(exc),
        )

    if not payload.get("ok"):
        return DeliveryAttempt(
            target_id=target_id,
            target_type="telegram_bot",
            mode=mode,
            ok=False,
            status="bot_api_error",
            error=_clean_text(payload.get("description") or payload, max_len=500),
        )
    message = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    return DeliveryAttempt(
        target_id=target_id,
        target_type="telegram_bot",
        mode=mode,
        ok=True,
        status="sent",
        message_id=str(message.get("message_id")) if message.get("message_id") is not None else None,
    )
