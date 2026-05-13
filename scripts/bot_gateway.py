"""Local-first Telegram Bot gateway for T-Sense.

The bot is a human interaction surface, not a shell gateway.  Incoming messages
are mapped to a small allowlist of local actions: status, latest results,
profiles, sources, dry-run scans, and Source assistant plans.  Mutating source
plans are previewed first and require an inline button confirmation from the
same chat before they are applied.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from scripts import bot_actions, bot_intents, dashboard_server, delivery, monitor_state
except ModuleNotFoundError:
    _PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    from scripts import bot_actions, bot_intents, dashboard_server, delivery, monitor_state


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / ".tgcs" / "tgcs.db"
DEFAULT_BOT_STATE_PATH = PROJECT_ROOT / ".tgcs" / "bot-gateway-state.json"
DEFAULT_BOT_LOCK_PATH = PROJECT_ROOT / ".tgcs" / "bot-gateway.lock"
BOT_ALLOWED_CHAT_IDS_ENV = "TGCS_BOT_ALLOWED_CHAT_IDS"
BOT_API_BASE_URL_ENV = "TGCS_BOT_API_BASE_URL"
BOT_API_TIMEOUT_SECONDS = 20
BOT_POLL_TIMEOUT_SECONDS = 30
MAX_TELEGRAM_MESSAGE_LENGTH = 3900
PENDING_SOURCE_PLAN_TTL_SECONDS = 15 * 60

BOT_COMMANDS = [
    {"command": "start", "description": "Show the T-Sense bot menu"},
    {"command": "help", "description": "Show commands and safe actions"},
    {"command": "status", "description": "Show setup, source, run, and inbox status"},
    {"command": "latest", "description": "Show the latest actionable results"},
    {"command": "scan", "description": "Run a dry scan for jobs-fast"},
    {"command": "sources", "description": "Show or adjust saved sources"},
    {"command": "profiles", "description": "List enabled profiles"},
    {"command": "settings", "description": "Show local setup guidance"},
]
BOT_DISPLAY_NAME = "T-Sense"
BOT_DESCRIPTION = (
    "T-Sense is a local-first Telegram signal desk. It shows status, latest review cards, "
    "dry-run scans, profiles, and source controls only while your local gateway is running."
)
BOT_SHORT_DESCRIPTION = "Local-first Telegram signal desk."
BOT_AVATAR_PATH = PROJECT_ROOT / "docs" / "brand" / "bot-avatar.jpg"

ALLOWED_INTENT_ACTIONS = bot_intents.ALLOWED_INTENT_ACTIONS
BotIntent = bot_intents.BotIntent


@dataclass
class PendingSourcePlan:
    chat_id: str
    topic: str
    resolved_plan: dict[str, list[str]]
    created_at: float


class BotGatewayError(Exception):
    """Raised when the local bot gateway cannot complete a safe action."""


def _lock_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True
    if sys.platform.startswith("win"):
        try:
            completed = subprocess.run(
                ["tasklist.exe", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                check=False,
                capture_output=True,
                text=True,
                timeout=2,
            )
        except (OSError, subprocess.TimeoutExpired):
            return True
        return completed.returncode == 0 and str(pid) in (completed.stdout or "")
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


def _read_lock_pid(path: Path) -> int:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return 0
    if not isinstance(payload, dict):
        return 0
    try:
        return int(payload.get("pid") or 0)
    except (TypeError, ValueError):
        return 0


class BotGatewayLock:
    def __init__(self, path: Path = DEFAULT_BOT_LOCK_PATH):
        self.path = path
        self.acquired = False

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            existing_pid = _read_lock_pid(self.path)
            if existing_pid and _lock_pid_alive(existing_pid):
                raise BotGatewayError("Bot Gateway is already running. Stop the existing local gateway before starting another one.")
            try:
                self.path.unlink()
            except OSError:
                raise BotGatewayError("Bot Gateway lock is stale but could not be cleared.") from None
        try:
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise BotGatewayError("Bot Gateway is already running. Stop the existing local gateway before starting another one.") from None
        payload = json.dumps({"schema_version": "bot_gateway_lock_v1", "pid": os.getpid(), "created_at": monitor_state.utc_now()})
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload + "\n")
        self.acquired = True
        return self

    def __exit__(self, exc_type, exc, tb):
        if self.acquired:
            try:
                if _read_lock_pid(self.path) == os.getpid():
                    self.path.unlink(missing_ok=True)
            except OSError:
                pass
        self.acquired = False
        return False


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
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
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
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
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

    def send_message(self, chat_id: str, text: str, *, reply_markup: dict[str, Any] | None = None) -> None:
        chunks = split_telegram_text(bot_actions.redact_telegram_reply(text))
        for index, chunk in enumerate(chunks):
            payload: dict[str, Any] = {
                "chat_id": chat_id,
                "text": chunk,
                "disable_web_page_preview": True,
            }
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


def load_state(path: Path = DEFAULT_BOT_STATE_PATH) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def save_state(state: dict[str, Any], path: Path = DEFAULT_BOT_STATE_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_gateway_state(
    path: Path = DEFAULT_BOT_STATE_PATH,
    *,
    offset: int | None,
    started_at: str,
    authorized_chat_count: int,
    commands_installed: bool,
    last_poll_at: str | None = None,
    pid: int | None = None,
) -> None:
    payload = {
        "schema_version": "bot_gateway_state_v1",
        "pid": int(pid if pid is not None else os.getpid()),
        "started_at": started_at,
        "last_poll_at": last_poll_at or monitor_state.utc_now(),
        "authorized_chat_count": max(0, int(authorized_chat_count)),
        "commands_installed": bool(commands_installed),
        "offset": offset,
    }
    save_state(payload, path)


def clean_chat_id(value: object) -> str:
    text = str(value or "").strip()
    return text if re.fullmatch(r"-?\d{5,20}", text) else ""


def allowed_chat_ids_from_env() -> set[str]:
    raw = os.environ.get(BOT_ALLOWED_CHAT_IDS_ENV, "")
    return {chat_id for chat_id in (clean_chat_id(part) for part in re.split(r"[,;\s]+", raw)) if chat_id}


def allowed_chat_ids_from_db(db_path: Path = DEFAULT_DB_PATH) -> set[str]:
    if not db_path.exists():
        return set()
    try:
        conn = monitor_state.connect(db_path)
    except Exception:
        return set()
    try:
        rows = conn.execute(
            "SELECT config_json FROM delivery_targets WHERE enabled = 1 AND target_type = ?",
            ("telegram_bot",),
        ).fetchall()
    finally:
        conn.close()
    allowed: set[str] = set()
    for row in rows:
        payload = monitor_state.parse_json(row["config_json"], {})
        if isinstance(payload, dict):
            config = payload.get("config") if isinstance(payload.get("config"), dict) else payload
            chat_id = clean_chat_id(config.get("chat_id"))
            if chat_id:
                allowed.add(chat_id)
    return allowed


def allowed_chat_ids(db_path: Path = DEFAULT_DB_PATH, extra: list[str] | None = None) -> set[str]:
    allowed = allowed_chat_ids_from_env() | allowed_chat_ids_from_db(db_path)
    for value in extra or []:
        chat_id = clean_chat_id(value)
        if chat_id:
            allowed.add(chat_id)
    return allowed


def chat_is_allowed(chat_id: str, *, allowed: set[str]) -> bool:
    return bool(chat_id and chat_id in allowed)


def main_menu_keyboard() -> dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "Status", "callback_data": "status"},
                {"text": "Latest", "callback_data": "latest"},
            ],
            [
                {"text": "Dry scan", "callback_data": "scan:jobs-fast"},
                {"text": "Sources", "callback_data": "sources"},
            ],
        ]
    }


def help_text() -> str:
    return "\n".join(
        [
            "T-Sense bot",
            "",
            "Commands:",
            "/status - setup, source, run, and inbox status",
            "/latest - latest actionable cards and report",
            "/scan - run jobs-fast in dry-run mode",
            "/sources - source count and topics",
            "/sources add @channel - preview a source change",
            "/profiles - enabled profiles",
            "/settings - local setup guidance",
            "",
            "Natural language works for the same safe actions. Source changes are previewed first and require the Apply button.",
        ]
    )


def dashboard_snapshot(db_path: Path = DEFAULT_DB_PATH) -> dict[str, Any]:
    conn = monitor_state.connect(db_path)
    try:
        return monitor_state.dashboard_snapshot(conn)
    finally:
        conn.close()


def source_summary() -> str:
    sources = dashboard_server.desk_sources()
    topics = ", ".join(sources.get("topics") or []) or "none"
    return "\n".join(
        [
            "Sources",
            f"Total: {sources.get('source_count', 0)}",
            f"Enabled: {sources.get('enabled_count', 0)}",
            f"Topics: {topics}",
            "",
            "Send: add @channel, pause @channel, remove @channel",
        ]
    )


def profile_summary(snapshot: dict[str, Any]) -> str:
    profiles = [item for item in snapshot.get("profiles") or [] if isinstance(item, dict)]
    if not profiles:
        return "No profiles are registered yet. Open Signal Desk Start or run ./tgcs init --starter jobs."
    lines = ["Profiles"]
    for profile in profiles[:12]:
        status = "enabled" if profile.get("enabled") else "muted"
        label = str(profile.get("display_name") or profile.get("profile_id") or "profile")
        lines.append(f"- {label}: {status}")
    if len(profiles) > 12:
        lines.append(f"... {len(profiles) - 12} more")
    return "\n".join(lines)


def status_summary(snapshot: dict[str, Any]) -> str:
    setup = snapshot.get("setup_status") if isinstance(snapshot.get("setup_status"), dict) else {}
    opportunity = snapshot.get("opportunity_summary") if isinstance(snapshot.get("opportunity_summary"), dict) else {}
    runs = [item for item in snapshot.get("runs") or [] if isinstance(item, dict)]
    inbox = [item for item in snapshot.get("inbox") or [] if isinstance(item, dict)]
    latest_run = runs[0] if runs else {}
    return "\n".join(
        [
            "T-Sense status",
            f"Stage: {setup.get('stage') or 'unknown'}",
            f"Next: {setup.get('next_step') or 'Open Signal Desk'}",
            f"Pending review cards: {len(inbox)}",
            f"Latest run: {latest_run.get('status') or 'none'} {latest_run.get('profile_id') or ''}".strip(),
            f"Opportunity summary: {opportunity.get('title') or opportunity.get('status') or 'not ready'}",
        ]
    )


def latest_summary(snapshot: dict[str, Any]) -> str:
    opportunity = snapshot.get("opportunity_summary") if isinstance(snapshot.get("opportunity_summary"), dict) else {}
    title = str(opportunity.get("title") or "Latest results")
    detail = str(opportunity.get("detail") or opportunity.get("status") or "No latest summary yet.")
    lines = [title, detail]
    items = opportunity.get("items")
    if isinstance(items, list):
        for item in items[:5]:
            if not isinstance(item, dict):
                continue
            label = str(item.get("title") or item.get("label") or item.get("card_title") or "Item")
            rating = str(item.get("rating") or item.get("status") or "").strip()
            lines.append(f"- {label}" + (f" ({rating})" if rating else ""))
    runs = [item for item in snapshot.get("runs") or [] if isinstance(item, dict)]
    if runs:
        artifact = runs[0].get("report_artifact") if isinstance(runs[0].get("report_artifact"), dict) else {}
        display_path = str(artifact.get("display_path") or artifact.get("path") or "")
        if display_path:
            lines.append(f"Report: {display_path}")
    return "\n".join(lines)


def latest_actionable_card(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    inbox = snapshot.get("inbox") if isinstance(snapshot.get("inbox"), list) else []
    for card in inbox:
        if not isinstance(card, dict):
            continue
        if str(card.get("opportunity_status") or "open").strip().lower() != "open":
            continue
        if str(card.get("card_id") or "").strip():
            return card
    return None


def lifecycle_keyboard(card: dict[str, Any]) -> dict[str, Any] | None:
    card_id = str(card.get("card_id") or "").strip()
    if not card_id:
        return None
    return {
        "inline_keyboard": [
            [
                {"text": "Applied", "callback_data": f"card:applied:{card_id}"},
                {"text": "Save", "callback_data": f"card:saved:{card_id}"},
            ],
            [
                {"text": "Contacted", "callback_data": f"card:contacted:{card_id}"},
                {"text": "Dismiss", "callback_data": f"card:dismissed:{card_id}"},
                {"text": "Duplicate", "callback_data": f"card:duplicate:{card_id}"},
            ],
        ]
    }


def lifecycle_status_label(status: object) -> str:
    labels = {
        "open": "Open",
        "saved": "Saved",
        "applied": "Applied",
        "contacted": "Contacted",
        "dismissed": "Dismissed",
        "duplicate": "Duplicate",
    }
    return labels.get(str(status or "open").strip().lower(), "Open")


def card_action_summary(card: dict[str, Any]) -> str:
    label = lifecycle_status_label(card.get("opportunity_status"))
    title = str(card.get("title") or "Review card").strip()
    rating = str(card.get("rating") or "").strip()
    detail = f"{label}: {title}"
    if rating:
        detail += f" ({rating})"
    return detail


def run_dry_scan(profile_id: str, *, timeout_seconds: int = 900) -> str:
    _ = timeout_seconds
    result = bot_actions.BotActionRegistry().execute(
        BotIntent(action="scan_profile_dry_run", args={"profile_id": profile_id})
    )
    if result.error_category:
        raise BotGatewayError(result.text)
    return result.text


def clean_topic(value: str) -> str:
    return bot_intents.clean_topic(value)


def deterministic_intent(text: str) -> BotIntent | None:
    return bot_intents.deterministic_intent(text)


def llm_intent(text: str) -> BotIntent | None:
    return bot_intents.llm_intent(text)


def route_text_to_intent(text: str, *, use_llm: bool = False) -> BotIntent:
    return bot_intents.route_text_to_intent(text, use_llm=use_llm)


def source_plan_preview(instruction: str, topic: str) -> tuple[str, dict[str, Any]]:
    # Telegram chat confirmation only authorizes applying the resolved local
    # plan. It is not a consent boundary for sending the saved source list to
    # an external model, so bot previews stay parser-only until Signal Desk
    # provides a dedicated AI source planning confirmation flow.
    result = dashboard_server.run_source_assistant(
        {
            "instruction": instruction,
            "topic": topic,
            "dry_run": True,
            "confirm_external_ai": False,
        }
    )
    lines = [
        result.get("title") or "Source plan ready",
        result.get("detail") or "Review the source plan before applying it.",
        f"Add {result.get('added_count', 0)} · Pause {result.get('disabled_count', 0)} · Resume {result.get('enabled_count', 0)} · Remove {result.get('removed_count', 0)}",
    ]
    preview_sources = result.get("preview_sources") if isinstance(result.get("preview_sources"), list) else []
    for source in preview_sources[:8]:
        if isinstance(source, dict):
            lines.append(f"- {source.get('label') or source.get('source_id')}")
    return "\n".join(lines), result


def apply_source_plan(resolved_plan: dict[str, list[str]], topic: str) -> str:
    result = dashboard_server.apply_source_assistant_resolved_plan(resolved_plan, topic)
    return "\n".join(
        [
            result.get("title") or "Source plan applied",
            f"Add {result.get('added_count', 0)} · Pause {result.get('disabled_count', 0)} · Resume {result.get('enabled_count', 0)} · Remove {result.get('removed_count', 0)}",
        ]
    )


class BotGateway:
    def __init__(
        self,
        api: TelegramBotApi,
        *,
        db_path: Path = DEFAULT_DB_PATH,
        use_llm: bool = False,
        allowed: set[str] | None = None,
        extra_allowed: list[str] | None = None,
    ):
        self.api = api
        self.db_path = db_path
        self.use_llm = use_llm
        self.extra_allowed = list(extra_allowed or [])
        self.fixed_allowed = allowed is not None
        self.allowed = allowed if allowed is not None else allowed_chat_ids(db_path, self.extra_allowed)
        self.pending_source_plans: dict[str, PendingSourcePlan] = {}
        self.action_registry = bot_actions.BotActionRegistry()

    def refresh_allowed(self) -> None:
        if not self.fixed_allowed:
            self.allowed = allowed_chat_ids(self.db_path, self.extra_allowed)

    def chat_is_allowed(self, chat_id: str) -> bool:
        self.refresh_allowed()
        return chat_is_allowed(chat_id, allowed=self.allowed)

    def send_message(self, chat_id: str, text: str, *, reply_markup: dict[str, Any] | None = None) -> None:
        self.api.send_message(chat_id, bot_actions.redact_telegram_reply(text), reply_markup=reply_markup)

    def prune_pending_source_plans(self) -> None:
        now = time.time()
        expired = [
            plan_id
            for plan_id, plan in self.pending_source_plans.items()
            if now - plan.created_at > PENDING_SOURCE_PLAN_TTL_SECONDS
        ]
        for plan_id in expired:
            self.pending_source_plans.pop(plan_id, None)

    def dispatch_intent(self, chat_id: str, intent: BotIntent) -> None:
        if intent.action == "help":
            self.send_message(chat_id, help_text(), reply_markup=main_menu_keyboard())
            return
        if intent.action == "status":
            self.send_message(chat_id, status_summary(dashboard_snapshot(self.db_path)))
            return
        if intent.action == "latest":
            snapshot = dashboard_snapshot(self.db_path)
            card = latest_actionable_card(snapshot)
            self.send_message(chat_id, latest_summary(snapshot), reply_markup=lifecycle_keyboard(card or {}))
            return
        if intent.action == "profiles":
            self.send_message(chat_id, profile_summary(dashboard_snapshot(self.db_path)))
            return
        if intent.action == "settings":
            self.send_message(chat_id, settings_text())
            return
        if intent.action == "sources_summary":
            self.send_message(chat_id, source_summary())
            return
        if intent.action == "knowledge_answer":
            result = self.action_registry.execute(intent)
            self.send_message(chat_id, result.text, reply_markup=result.reply_markup)
            return
        if intent.action in {"scan", "scan_profile_dry_run"}:
            if intent.profile_id == "jobs-fast":
                self.send_message(chat_id, f"Running {intent.profile_id} as dry-run. This can take a minute.")
            result = self.action_registry.execute(
                BotIntent(action="scan_profile_dry_run", args={"profile_id": intent.profile_id})
            )
            self.send_message(chat_id, result.text, reply_markup=result.reply_markup)
            return
        if intent.action == "sources_plan":
            if not intent.instruction:
                self.send_message(chat_id, "Send a source instruction such as: add @remote_jobs or remove @old_jobs.")
                return
            preview, result = source_plan_preview(intent.instruction, intent.topic)
            operation_count = sum(int(result.get(key) or 0) for key in ("added_count", "updated_count", "removed_count", "enabled_count", "disabled_count"))
            if operation_count <= 0:
                self.send_message(chat_id, preview)
                return
            resolved_plan = result.get("resolved_plan") if isinstance(result.get("resolved_plan"), dict) else {}
            plan_id = secrets.token_urlsafe(8)
            self.prune_pending_source_plans()
            self.pending_source_plans[plan_id] = PendingSourcePlan(
                chat_id=chat_id,
                topic=intent.topic,
                resolved_plan=resolved_plan,
                created_at=time.time(),
            )
            self.send_message(
                chat_id,
                preview,
                reply_markup={"inline_keyboard": [[{"text": "Apply source plan", "callback_data": f"sources_apply:{plan_id}"}]]},
            )
            return
        self.send_message(chat_id, help_text(), reply_markup=main_menu_keyboard())

    def handle_text(self, chat_id: str, text: str) -> None:
        if not self.chat_is_allowed(chat_id):
            self.send_message(chat_id, unauthorized_text(), reply_markup=main_menu_keyboard())
            return
        intent = route_text_to_intent(text, use_llm=self.use_llm)
        self.dispatch_intent(chat_id, intent)

    def handle_callback(self, chat_id: str, callback_query_id: str, data: str) -> None:
        if not self.chat_is_allowed(chat_id):
            self.api.answer_callback_query(callback_query_id, "Open Signal Desk Settings to authorize this chat.")
            self.send_message(chat_id, unauthorized_text())
            return
        if data == "status":
            self.api.answer_callback_query(callback_query_id)
            self.dispatch_intent(chat_id, BotIntent(action="status"))
            return
        if data == "latest":
            self.api.answer_callback_query(callback_query_id)
            self.dispatch_intent(chat_id, BotIntent(action="latest"))
            return
        if data == "sources":
            self.api.answer_callback_query(callback_query_id)
            self.dispatch_intent(chat_id, BotIntent(action="sources_summary"))
            return
        if data.startswith("scan:"):
            self.api.answer_callback_query(callback_query_id, "Starting dry scan")
            self.dispatch_intent(
                chat_id,
                BotIntent(action="scan_profile_dry_run", args={"profile_id": data.split(":", 1)[1] or "jobs-fast"}),
            )
            return
        if data.startswith("sources_apply:"):
            self.prune_pending_source_plans()
            plan_id = data.split(":", 1)[1]
            plan = self.pending_source_plans.get(plan_id)
            if not plan or plan.chat_id != chat_id:
                self.api.answer_callback_query(callback_query_id, "Source plan expired.")
                return
            self.api.answer_callback_query(callback_query_id, "Applying source plan")
            self.send_message(chat_id, apply_source_plan(plan.resolved_plan, plan.topic))
            self.pending_source_plans.pop(plan_id, None)
            return
        if data.startswith("card:"):
            parts = data.split(":", 2)
            if len(parts) != 3:
                self.api.answer_callback_query(callback_query_id, "Card action expired.")
                return
            _, action, card_id = parts
            if action not in monitor_state.LIFECYCLE_ACTIONS:
                self.api.answer_callback_query(callback_query_id, "Unsupported card action.")
                return
            try:
                conn = monitor_state.connect(self.db_path)
                try:
                    card = monitor_state.set_card_action(conn, card_id=card_id, action=action)
                finally:
                    conn.close()
            except monitor_state.MonitorStateError:
                self.api.answer_callback_query(callback_query_id, "Card is no longer available.")
                return
            label = lifecycle_status_label(card.get("opportunity_status"))
            self.api.answer_callback_query(callback_query_id, f"Marked {label}")
            self.send_message(chat_id, card_action_summary(card), reply_markup=lifecycle_keyboard(card) if card.get("opportunity_status") == "open" else None)
            return
        self.api.answer_callback_query(callback_query_id, "Unsupported action")

    def handle_update(self, update: dict[str, Any]) -> None:
        callback = update.get("callback_query")
        if isinstance(callback, dict):
            message = callback.get("message") if isinstance(callback.get("message"), dict) else {}
            chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
            chat_id = clean_chat_id(chat.get("id"))
            data = str(callback.get("data") or "")
            callback_id = str(callback.get("id") or "")
            if chat_id and callback_id:
                self.handle_callback(chat_id, callback_id, data)
            return
        message = update.get("message")
        if not isinstance(message, dict):
            return
        chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
        chat_id = clean_chat_id(chat.get("id"))
        text = str(message.get("text") or "").strip()
        if chat_id and text:
            self.handle_text(chat_id, text)


def unauthorized_text() -> str:
    return "\n".join(
        [
            "This chat is not authorized for T-Sense actions.",
            "Open Signal Desk Settings > Alerts, detect and save this bot chat, then try again.",
            "CLI fallback: TGCS_BOT_ALLOWED_CHAT_IDS=<chat_id> ./tgcs bot run",
        ]
    )


def settings_text() -> str:
    return "\n".join(
        [
            "Settings",
            "- Save the Telegram bot token in Signal Desk Settings > Alerts.",
            "- Detect and save this chat ID before using bot actions.",
            "- Keep Signal Desk or ./tgcs bot run active for local-first bot control.",
            "- Cloud webhook and Mini App support are tracked as a later roadmap phase.",
        ]
    )


def install_menu() -> None:
    TelegramBotApi(load_bot_token()).set_my_commands()


def apply_bot_identity(api: TelegramBotApi | None = None) -> dict[str, Any]:
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
    run_step("menu_button", bot_api.set_chat_menu_button)
    run_step("profile_photo", lambda: bot_api.set_my_profile_photo(BOT_AVATAR_PATH))
    return {
        "schema_version": "bot_identity_apply_result_v1",
        "name": BOT_DISPLAY_NAME,
        "description_updated": bool(steps["description"]["ok"]),
        "short_description_updated": bool(steps["short_description"]["ok"]),
        "commands_installed": bool(steps["commands"]["ok"]),
        "menu_button_updated": bool(steps["menu_button"]["ok"]),
        "profile_photo_updated": bool(steps["profile_photo"]["ok"]),
        "steps": steps,
    }


def run_loop(args: argparse.Namespace) -> int:
    with BotGatewayLock(Path(args.lock)):
        token = load_bot_token()
        api = TelegramBotApi(token)
        commands_installed = False
        if not args.skip_menu:
            api.set_my_commands()
            commands_installed = True
        extra_allowed = args.allow_chat_id or []
        gateway = BotGateway(api, db_path=Path(args.db), use_llm=bool(args.llm) and not args.no_llm, extra_allowed=extra_allowed)
        state_path = Path(args.state)
        state = load_state(state_path)
        offset = state.get("offset") if isinstance(state.get("offset"), int) else None
        started_at = monitor_state.utc_now()
        write_gateway_state(
            state_path,
            offset=offset,
            started_at=started_at,
            authorized_chat_count=len(gateway.allowed),
            commands_installed=commands_installed,
        )
        print("T-Sense bot gateway is running. Press Ctrl+C to stop.", flush=True)
        print(f"Authorized chats: {len(gateway.allowed)}", flush=True)
        while True:
            updates = api.get_updates(offset=offset, timeout_seconds=args.poll_timeout)
            gateway.refresh_allowed()
            for update in updates:
                update_id = update.get("update_id")
                if isinstance(update_id, int):
                    offset = update_id + 1
                gateway.handle_update(update)
            write_gateway_state(
                state_path,
                offset=offset,
                started_at=started_at,
                authorized_chat_count=len(gateway.allowed),
                commands_installed=commands_installed,
            )


def autostart_status() -> dict[str, Any]:
    conn = monitor_state.connect(DEFAULT_DB_PATH)
    try:
        return dashboard_server.desk_bot_gateway_status(conn)
    finally:
        conn.close()


def install_autostart() -> dict[str, Any]:
    return dashboard_server.run_desk_action("bot_gateway_install_autostart", body={"confirm": True})


def remove_autostart() -> dict[str, Any]:
    return dashboard_server.run_desk_action("bot_gateway_remove_autostart", body={"confirm": True})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local T-Sense Telegram Bot gateway.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Long-poll Telegram Bot updates and run safe local actions.")
    run.add_argument("--db", default=str(DEFAULT_DB_PATH))
    run.add_argument("--state", default=str(DEFAULT_BOT_STATE_PATH))
    run.add_argument("--lock", default=str(DEFAULT_BOT_LOCK_PATH))
    run.add_argument("--allow-chat-id", action="append", default=[], help="Authorize a Telegram chat id for this process.")
    run.add_argument("--poll-timeout", type=int, default=BOT_POLL_TIMEOUT_SECONDS)
    run.add_argument("--install-menu", action="store_true", help="Install the Telegram command menu before polling; this is now the default.")
    run.add_argument("--skip-menu", action="store_true", help="Skip command menu installation before polling.")
    run.add_argument("--llm", action="store_true", help="Opt in to optional LLM routing and knowledge answers for free-form messages.")
    run.add_argument("--no-llm", action="store_true", help="Keep free-form routing and knowledge answers local-only; this is the default.")
    run.set_defaults(func=run_loop)

    menu = subparsers.add_parser("install-menu", help="Install Telegram Bot command menu.")
    menu.set_defaults(func=lambda _args: install_menu() or 0)
    identity = subparsers.add_parser("apply-identity", help="Apply T-Sense bot name, descriptions, and command menu.")
    identity.set_defaults(func=lambda _args: print(json.dumps(apply_bot_identity(), ensure_ascii=False)) or 0)
    status = subparsers.add_parser("status", help="Show local Bot Gateway and background status.")
    status.set_defaults(func=lambda _args: print(json.dumps(autostart_status(), ensure_ascii=False)) or 0)
    install_bg = subparsers.add_parser("install-autostart", help="Start Bot Gateway automatically at user login.")
    install_bg.set_defaults(func=lambda _args: print(json.dumps(install_autostart(), ensure_ascii=False)) or 0)
    remove_bg = subparsers.add_parser("remove-autostart", help="Remove the Bot Gateway login task.")
    remove_bg.set_defaults(func=lambda _args: print(json.dumps(remove_autostart(), ensure_ascii=False)) or 0)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        return 130
    except BotGatewayError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
