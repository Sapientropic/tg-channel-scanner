"""Telegram Bot API wrapper and identity helpers."""

from __future__ import annotations

import http.client
import json
import os
import secrets
import sys
import urllib.error
import urllib.request
from ipaddress import ip_address
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from scripts import bot_actions, delivery
except ModuleNotFoundError:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts import bot_actions, delivery

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BOT_API_BASE_URL_ENV = "TGCS_BOT_API_BASE_URL"
BOT_API_TIMEOUT_SECONDS = 20
BOT_POLL_TIMEOUT_SECONDS = 30
MAX_TELEGRAM_MESSAGE_LENGTH = 3900
BOT_API_REQUEST_ERRORS = (
    urllib.error.URLError,
    TimeoutError,
    OSError,
    http.client.HTTPException,
    json.JSONDecodeError,
)
BOT_COMMANDS = [
    {"command": "start", "description": "Show the T-Sense bot menu"},
    {"command": "help", "description": "Show commands and safe actions"},
    {"command": "status", "description": "Show setup, source, run, and inbox status"},
    {"command": "latest", "description": "Show the latest actionable results"},
    {"command": "scan", "description": "Run an AI review for jobs-fast"},
    {"command": "sources", "description": "Show or adjust saved sources"},
    {"command": "profiles", "description": "List enabled profiles"},
    {"command": "settings", "description": "Show local setup guidance"},
]
BOT_DISPLAY_NAME = "T-Sense"
BOT_DESCRIPTION = (
    "T-Sense is a local-first Telegram signal desk. It shows status, latest review cards, "
    "AI reviews, profiles, and source controls only while your local gateway is running."
)
BOT_SHORT_DESCRIPTION = "Local-first Telegram signal desk."
BOT_AVATAR_PATH = PROJECT_ROOT / "docs" / "brand" / "bot-avatar.jpg"
BOT_MINIAPP_MENU_SCHEMA_VERSION = "bot_miniapp_menu_result_v1"
BOT_MINIAPP_MENU_TEXT_MAX_LENGTH = 64



class BotGatewayError(Exception):
    """Raised when the local bot gateway cannot complete a safe action."""



class TelegramBotApi:
    def __init__(self, token: str, *, timeout_seconds: int = BOT_API_TIMEOUT_SECONDS, api_base_url: str | None = None):
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.api_base_url = (api_base_url or os.environ.get(BOT_API_BASE_URL_ENV) or "https://api.telegram.org").rstrip("/")

    def method_url(self, method: str) -> str:
        return f"{self.api_base_url}/bot{self.token}/{method}"

    def request(self, method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        url = self.method_url(method)
        data = json.dumps(payload or {}).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
        except BOT_API_REQUEST_ERRORS as exc:
            raise BotGatewayError(f"Telegram Bot API request failed: {method}") from exc
        if not isinstance(result, dict) or result.get("ok") is not True:
            description = result.get("description") if isinstance(result, dict) else ""
            raise BotGatewayError(f"Telegram Bot API rejected {method}: {description or 'unknown error'}")
        return result

    def request_multipart(
        self,
        method: str,
        fields: dict[str, str],
        files: dict[str, tuple[str, bytes, str]],
    ) -> dict[str, Any]:
        boundary = "----tgcs-bot-boundary-" + secrets.token_urlsafe(12)
        body = bytearray()
        for name, value in fields.items():
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
            body.extend(value.encode("utf-8"))
            body.extend(b"\r\n")
        for name, (filename, content, content_type) in files.items():
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(
                (
                    f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'
                    f"Content-Type: {content_type}\r\n\r\n"
                ).encode("utf-8")
            )
            body.extend(content)
            body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))
        request = urllib.request.Request(
            self.method_url(method),
            data=bytes(body),
            method="POST",
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                result = json.loads(response.read().decode("utf-8"))
        except BOT_API_REQUEST_ERRORS as exc:
            raise BotGatewayError(f"Telegram Bot API request failed: {method}") from exc
        if not isinstance(result, dict) or result.get("ok") is not True:
            description = result.get("description") if isinstance(result, dict) else ""
            raise BotGatewayError(f"Telegram Bot API rejected {method}: {description or 'unknown error'}")
        return result

    def get_updates(self, *, offset: int | None, timeout_seconds: int = BOT_POLL_TIMEOUT_SECONDS) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timeout": timeout_seconds,
            "limit": 20,
            "allowed_updates": ["message", "callback_query"],
        }
        if offset is not None:
            payload["offset"] = offset
        result = self.request("getUpdates", payload)
        updates = result.get("result")
        return [item for item in updates if isinstance(item, dict)] if isinstance(updates, list) else []

    def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        reply_markup: dict[str, Any] | None = None,
        parse_mode: str | None = "Markdown",
    ) -> None:
        chunks = split_telegram_text(bot_actions.redact_telegram_reply(text))
        for index, chunk in enumerate(chunks):
            payload: dict[str, Any] = {
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            }
            if parse_mode:
                payload["parse_mode"] = parse_mode
            if reply_markup and index == len(chunks) - 1:
                payload["reply_markup"] = reply_markup
            self.request("sendMessage", payload)

    def answer_callback_query(self, callback_query_id: str, text: str = "") -> None:
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text[:180]
        self.request("answerCallbackQuery", payload)

    def set_my_commands(self) -> None:
        self.request("setMyCommands", {"commands": BOT_COMMANDS})

    def set_my_name(self, name: str) -> None:
        self.request("setMyName", {"name": name})

    def set_my_description(self, description: str) -> None:
        self.request("setMyDescription", {"description": description})

    def set_my_short_description(self, short_description: str) -> None:
        self.request("setMyShortDescription", {"short_description": short_description})

    def set_chat_menu_button(self) -> None:
        self.request("setChatMenuButton", {"menu_button": {"type": "commands"}})

    def set_miniapp_menu_button(self, *, text: str, url: str) -> None:
        self.request(
            "setChatMenuButton",
            {
                "menu_button": {
                    "type": "web_app",
                    "text": clean_miniapp_menu_text(text),
                    "web_app": {"url": clean_miniapp_menu_url(url)},
                }
            },
        )

    def set_my_profile_photo(self, photo_path: Path | str) -> None:
        path = Path(photo_path)
        if path.suffix.casefold() not in {".jpg", ".jpeg"}:
            raise BotGatewayError("Bot profile photo asset must be a JPG image.")
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise BotGatewayError("Bot profile photo asset is not available.") from exc
        attach_name = "profile_photo"
        payload = {"type": "static", "photo": f"attach://{attach_name}"}
        self.request_multipart(
            "setMyProfilePhoto",
            {"photo": json.dumps(payload, separators=(",", ":"))},
            {attach_name: ("bot-avatar.jpg", content, "image/jpeg")},
        )



def split_telegram_text(text: str) -> list[str]:
    clean = text.strip() or "Done."
    if len(clean) <= MAX_TELEGRAM_MESSAGE_LENGTH:
        return [clean]
    chunks: list[str] = []
    remaining = clean
    while len(remaining) > MAX_TELEGRAM_MESSAGE_LENGTH:
        cut = remaining.rfind("\n", 0, MAX_TELEGRAM_MESSAGE_LENGTH)
        if cut < 500:
            cut = MAX_TELEGRAM_MESSAGE_LENGTH
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks



def load_bot_token() -> str:
    token = delivery.resolve_telegram_bot_token().token
    if not token:
        raise BotGatewayError("Telegram bot token is not configured. Save it in Signal Desk Settings first.")
    return token


def clean_miniapp_menu_text(value: str) -> str:
    text = " ".join(str(value or "").split()) or "Review"
    if len(text) > BOT_MINIAPP_MENU_TEXT_MAX_LENGTH:
        raise BotGatewayError("Telegram Mini App menu text is too long.")
    return text


def clean_miniapp_menu_url(value: str) -> str:
    url = str(value or "").strip()
    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise BotGatewayError("Telegram Mini App URL is invalid.") from exc
    if parsed.scheme != "https" or not parsed.netloc:
        raise BotGatewayError("Telegram Mini App URL must be an HTTPS URL.")
    hostname = (parsed.hostname or "").casefold()
    if hostname in {"localhost", "127.0.0.1", "::1"} or hostname.endswith(".localhost"):
        raise BotGatewayError("Telegram Mini App URL must be public HTTPS, not localhost.")
    try:
        address = ip_address(hostname.strip("[]"))
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise BotGatewayError("Telegram Mini App URL must be public HTTPS, not a private address.")
    return url


def install_miniapp_menu(
    url: str,
    *,
    api: TelegramBotApi | None = None,
    text: str = "Review",
    dry_run: bool = False,
) -> dict[str, Any]:
    clean_url = clean_miniapp_menu_url(url)
    clean_text = clean_miniapp_menu_text(text)
    if dry_run:
        return {
            "schema_version": BOT_MINIAPP_MENU_SCHEMA_VERSION,
            "menu_button_updated": False,
            "dry_run": True,
            "text": clean_text,
            "url": clean_url,
            "next_step": "Run the same command without --dry-run when this public HTTPS Mini App URL is ready.",
        }
    bot_api = api or TelegramBotApi(load_bot_token())
    bot_api.set_miniapp_menu_button(text=clean_text, url=clean_url)
    return {
        "schema_version": BOT_MINIAPP_MENU_SCHEMA_VERSION,
        "menu_button_updated": True,
        "dry_run": False,
        "text": clean_text,
        "url": clean_url,
    }



def apply_bot_identity(api: TelegramBotApi | None = None, *, preserve_menu_button: bool = False) -> dict[str, Any]:
    bot_api = api or TelegramBotApi(load_bot_token())
    steps: dict[str, dict[str, Any]] = {}

    def run_step(name: str, operation) -> None:
        try:
            operation()
        except Exception as exc:
            # Identity setup is a setup convenience, not a critical runtime path.
            # Keep going so a missing/invalid avatar does not prevent commands or
            # descriptions from being applied, and never echo local paths or tokens.
            steps[name] = {
                "ok": False,
                "error": bot_actions.redact_telegram_reply(str(exc))[:500],
            }
        else:
            steps[name] = {"ok": True, "error": ""}

    run_step("name", lambda: bot_api.set_my_name(BOT_DISPLAY_NAME))
    run_step("description", lambda: bot_api.set_my_description(BOT_DESCRIPTION))
    run_step("short_description", lambda: bot_api.set_my_short_description(BOT_SHORT_DESCRIPTION))
    run_step("commands", bot_api.set_my_commands)
    if preserve_menu_button:
        steps["menu_button"] = {"ok": True, "error": "", "mode": "preserved"}
    else:
        run_step("menu_button", bot_api.set_chat_menu_button)
    run_step("profile_photo", lambda: bot_api.set_my_profile_photo(BOT_AVATAR_PATH))
    return {
        "schema_version": "bot_identity_apply_result_v1",
        "name": BOT_DISPLAY_NAME,
        "description_updated": bool(steps["description"]["ok"]),
        "short_description_updated": bool(steps["short_description"]["ok"]),
        "commands_installed": bool(steps["commands"]["ok"]),
        "menu_button_updated": bool(steps["menu_button"]["ok"] and not preserve_menu_button),
        "menu_button_mode": "preserved" if preserve_menu_button else "commands",
        "profile_photo_updated": bool(steps["profile_photo"]["ok"]),
        "steps": steps,
    }
