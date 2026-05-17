"""Local Bot Gateway state, lock, and chat authorization helpers."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from scripts import monitor_state
    from scripts.bot_api import BotGatewayError
except ModuleNotFoundError:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts import monitor_state
    from scripts.bot_api import BotGatewayError

PROJECT_ROOT_ENV = "TGCS_PROJECT_ROOT"


def _default_project_root() -> Path:
    explicit_root = os.environ.get(PROJECT_ROOT_ENV, "").strip()
    if explicit_root:
        return Path(explicit_root).expanduser()
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = _default_project_root()
DEFAULT_DB_PATH = PROJECT_ROOT / ".tgcs" / "tgcs.db"
DEFAULT_BOT_STATE_PATH = PROJECT_ROOT / ".tgcs" / "bot-gateway-state.json"
DEFAULT_BOT_LOCK_PATH = PROJECT_ROOT / ".tgcs" / "bot-gateway.lock"
BOT_ALLOWED_CHAT_IDS_ENV = "TGCS_BOT_ALLOWED_CHAT_IDS"
BOT_GATEWAY_LOCK_OWNER = "tgcs-bot-gateway"



@dataclass
class PendingSourcePlan:
    chat_id: str
    topic: str
    resolved_plan: dict[str, list[str]]
    created_at: float



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


def _process_command_line(pid: int) -> str | None:
    if pid <= 0:
        return None
    if sys.platform.startswith("win"):
        try:
            completed = subprocess.run(
                [
                    "wmic",
                    "process",
                    "where",
                    f"ProcessId={pid}",
                    "get",
                    "CommandLine",
                    "/value",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=2,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if completed.returncode != 0:
            return None
        return (completed.stdout or "").strip() or None

    proc_cmdline = Path(f"/proc/{pid}/cmdline")
    try:
        raw = proc_cmdline.read_bytes()
    except OSError:
        raw = b""
    if raw:
        return raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip() or None

    try:
        completed = subprocess.run(
            ["ps", "-p", str(pid), "-o", "command="],
            check=False,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return (completed.stdout or "").strip() or None


def _command_line_looks_like_gateway(command: str) -> bool:
    text = " ".join(command.casefold().replace("\\", "/").split())
    if "bot_gateway.py" in text:
        return True
    return "tgcs" in text and " bot " in f" {text} " and " run" in f" {text} "


def _read_lock_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_lock_pid(path: Path) -> int:
    payload = _read_lock_payload(path)
    try:
        return int(payload.get("pid") or 0)
    except (TypeError, ValueError):
        return 0


def _lock_claims_active_gateway(payload: dict[str, Any]) -> bool:
    try:
        pid = int(payload.get("pid") or 0)
    except (TypeError, ValueError):
        return False
    owner = str(payload.get("owner") or "")
    if owner and owner != BOT_GATEWAY_LOCK_OWNER:
        return False
    if not _lock_pid_alive(pid):
        return False
    if pid == os.getpid():
        return True

    command = _process_command_line(pid)
    if command is None:
        # If the platform refuses process inspection, keep the conservative
        # single-gateway guard. Clearing an uninspectable live PID could start
        # two gateways against the same bot token and duplicate user actions.
        return True
    return _command_line_looks_like_gateway(command)


class BotGatewayLock:
    def __init__(self, path: Path = DEFAULT_BOT_LOCK_PATH):
        self.path = path
        self.acquired = False

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            existing_payload = _read_lock_payload(self.path)
            if _lock_claims_active_gateway(existing_payload):
                raise BotGatewayError("Bot Gateway is already running. Stop the existing local gateway before starting another one.")
            try:
                self.path.unlink()
            except OSError:
                raise BotGatewayError("Bot Gateway lock is stale but could not be cleared.") from None
        try:
            fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise BotGatewayError("Bot Gateway is already running. Stop the existing local gateway before starting another one.") from None
        payload = json.dumps(
            {
                "schema_version": "bot_gateway_lock_v1",
                "owner": BOT_GATEWAY_LOCK_OWNER,
                "pid": os.getpid(),
                "created_at": monitor_state.utc_now(),
            }
        )
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
    last_error: str = "",
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
    if last_error:
        payload["last_error"] = str(last_error)[:500]
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
