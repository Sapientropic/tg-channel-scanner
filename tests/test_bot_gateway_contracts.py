import json
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from scripts import bot_gateway, dashboard_server, monitor_state


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "contracts" / "desk_bot_gateway_status_v1.json"
BOT_GATEWAY_STATUS_KEYS = (
    "schema_version",
    "token_configured",
    "authorized_chat_count",
    "gateway_status",
    "commands_installed",
    "supported_commands",
    "local_first_note",
    "start_command",
    "last_update_at",
    "last_error",
    "safe_next_action",
    "started_at",
    "last_poll_at",
)
BOT_GATEWAY_BACKGROUND_KEYS = (
    "schema_version",
    "backend",
    "available",
    "installed",
    "status",
    "can_install",
    "can_remove",
    "detail",
    "next_action",
    "checked_at",
)
BOT_IDENTITY_KEYS = (
    "schema_version",
    "name",
    "description_updated",
    "short_description_updated",
    "commands_installed",
    "menu_button_updated",
    "profile_photo_updated",
)


def load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def bot_gateway_status_contract(status: dict) -> dict:
    return {
        **{key: status.get(key) for key in BOT_GATEWAY_STATUS_KEYS},
        "background": {
            key: status.get("background", {}).get(key)
            for key in BOT_GATEWAY_BACKGROUND_KEYS
        },
    }


def bot_identity_contract(result: dict) -> dict:
    return {key: result.get(key) for key in BOT_IDENTITY_KEYS}


class FakeIdentityApi:
    def set_my_name(self, name):
        self.name = name

    def set_my_description(self, description):
        self.description = description

    def set_my_short_description(self, short_description):
        self.short_description = short_description

    def set_my_commands(self):
        self.commands = True

    def set_chat_menu_button(self):
        self.menu_button = True

    def set_my_profile_photo(self, photo_path):
        self.profile_photo = Path(photo_path).name


class BotGatewayContractTests(unittest.TestCase):
    def test_bot_gateway_status_fixture_matches_backend_without_sensitive_fields(self):
        fixture = load_fixture()
        expected = fixture["bot_gateway"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_path = root / ".tgcs" / dashboard_server.DESK_BOT_GATEWAY_STATE_FILENAME
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(
                json.dumps(
                    {
                        "schema_version": "bot_gateway_state_v1",
                        "pid": 123,
                        "started_at": expected["started_at"],
                        "last_poll_at": expected["last_poll_at"],
                        "authorized_chat_count": expected["authorized_chat_count"],
                        "commands_installed": expected["commands_installed"],
                        "last_error": (
                            "TGCS_TELEGRAM_BOT_TOKEN=BOT_GATEWAY_TOKEN_SHOULD_NOT_SURFACE "
                            "chat_id=12345678901 C:\\Users\\Administrator\\private\\bot-gateway-state.json"
                        ),
                        "offset": 9,
                    }
                ),
                encoding="utf-8",
            )
            conn = monitor_state.connect(root / ".tgcs" / "tgcs.db")
            try:
                with patch.object(dashboard_server, "PROJECT_ROOT", root):
                    with patch.object(dashboard_server.sys, "platform", "win32"):
                        with patch.object(
                            dashboard_server,
                            "desk_notification_token_status",
                            return_value={"configured": True, "source": "keyring"},
                        ):
                            with patch.object(
                                dashboard_server,
                                "_run_scheduler_command",
                                return_value=subprocess.CompletedProcess(["schtasks.exe"], 0, stdout="", stderr=""),
                            ):
                                with patch.object(
                                    dashboard_server,
                                    "_utc_now",
                                    return_value=expected["background"]["checked_at"],
                                ):
                                    status = dashboard_server.desk_bot_gateway_status(
                                        conn,
                                        now=datetime(2026, 5, 12, 12, 1, tzinfo=UTC),
                                    )
            finally:
                conn.close()

        self.assertEqual(bot_gateway_status_contract(status), bot_gateway_status_contract(expected))
        surfaced = json.dumps(status, ensure_ascii=False, sort_keys=True)
        for denied in fixture["denied_strings"]:
            with self.subTest(denied=denied):
                self.assertNotIn(denied, surfaced)

    def test_bot_identity_fixture_matches_apply_result_without_sensitive_fields(self):
        fixture = load_fixture()
        result = bot_gateway.apply_bot_identity(FakeIdentityApi())

        self.assertEqual(bot_identity_contract(result), bot_identity_contract(fixture["identity"]))
        surfaced = json.dumps(result, ensure_ascii=False, sort_keys=True)
        for denied in fixture["denied_strings"]:
            with self.subTest(denied=denied):
                self.assertNotIn(denied, surfaced)


if __name__ == "__main__":
    unittest.main()
