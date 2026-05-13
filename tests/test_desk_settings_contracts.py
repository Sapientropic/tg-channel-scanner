import json
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import dashboard_server


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "contracts" / "desk_settings_status_v1.json"
STATUS_CONTRACT_KEYS = (
    "schema_version",
    "configured",
    "source",
    "updated_at",
    "env_configured",
    "local_store_supported",
    "local_store_configured",
    "local_store_backend",
    "local_store_label",
    "can_save",
    "can_clear",
    "platform",
)
AI_SETTINGS_CONTRACT_KEYS = (
    "schema_version",
    "configured_count",
    "local_store_supported",
    "local_store_backend",
    "local_store_label",
    "platform",
)
AI_PROVIDER_CONTRACT_KEYS = (
    "provider",
    "label",
    "env_name",
    "configured",
    "source",
    "env_configured",
    "local_store_configured",
    "local_store_backend",
    "local_store_label",
    "can_save",
    "can_clear",
    "updated_at",
)


def load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def token_status_contract(status: dict) -> dict:
    return {key: status.get(key) for key in STATUS_CONTRACT_KEYS}


def ai_settings_contract(status: dict) -> dict:
    return {
        **{key: status.get(key) for key in AI_SETTINGS_CONTRACT_KEYS},
        "providers": [
            {key: provider.get(key) for key in AI_PROVIDER_CONTRACT_KEYS}
            for provider in status.get("providers", [])
            if isinstance(provider, dict)
        ],
    }


def assert_display_detail(testcase: unittest.TestCase, payload: dict) -> None:
    testcase.assertIsInstance(payload.get("detail"), str)
    testcase.assertTrue(payload["detail"].strip())


class DeskSettingsContractTests(unittest.TestCase):
    def test_settings_status_contracts_do_not_surface_keys_or_tokens(self):
        fixture = load_fixture()
        notification_target = dashboard_server.delivery.TELEGRAM_BOT_TOKEN_CREDENTIAL_TARGET
        deepseek_target = dashboard_server.DESK_AI_PROVIDER_CONFIGS["deepseek"]["target"]
        secrets = {
            notification_target: dashboard_server.local_credentials.StoredSecret(
                secret="LOCAL_NOTIFICATION_TOKEN_SHOULD_NOT_SURFACE",
                updated_at="2026-05-10T00:00:00Z",
            ),
            deepseek_target: dashboard_server.local_credentials.StoredSecret(
                secret="LOCAL_DEEPSEEK_KEY_SHOULD_NOT_SURFACE",
                updated_at="2026-05-10T00:00:00Z",
            ),
        }

        def fake_read_secret(target_name):
            return secrets.get(target_name)

        with patch.dict(
            "os.environ",
            {
                dashboard_server.delivery.TELEGRAM_BOT_TOKEN_ENV: "ENV_NOTIFICATION_TOKEN_SHOULD_NOT_SURFACE",
                "DEEPSEEK_API_KEY": "ENV_DEEPSEEK_KEY_SHOULD_NOT_SURFACE",
            },
            clear=True,
        ):
            with patch.object(dashboard_server.sys, "platform", "test-platform"):
                with patch.object(dashboard_server.local_credentials, "is_supported", return_value=True):
                    with patch.object(dashboard_server.local_credentials, "backend", return_value="keyring", create=True):
                        with patch.object(
                            dashboard_server.local_credentials,
                            "store_label",
                            return_value="Test Keyring",
                            create=True,
                        ):
                            with patch.object(
                                dashboard_server.local_credentials,
                                "read_secret",
                                side_effect=fake_read_secret,
                            ):
                                notification = dashboard_server.desk_notification_token_status()
                                ai_settings = dashboard_server.desk_ai_settings_status()

        self.assertEqual(token_status_contract(notification), token_status_contract(fixture["notification_token"]))
        self.assertEqual(ai_settings_contract(ai_settings), ai_settings_contract(fixture["ai_settings"]))
        assert_display_detail(self, notification)
        assert_display_detail(self, ai_settings)
        for provider in ai_settings["providers"]:
            assert_display_detail(self, provider)
        surfaced = json.dumps(
            {"notification_token": notification, "ai_settings": ai_settings},
            ensure_ascii=False,
            sort_keys=True,
        )
        for denied in fixture["denied_strings"]:
            with self.subTest(denied=denied):
                self.assertNotIn(denied, surfaced)


if __name__ == "__main__":
    unittest.main()
