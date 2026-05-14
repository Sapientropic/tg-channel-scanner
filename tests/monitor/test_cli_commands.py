import io
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from scripts import agent_cli, monitor, monitor_cli_commands, monitor_runner


class MonitorCliCommandTests(unittest.TestCase):
    def test_auxiliary_command_facades_delegate_to_cli_command_owner(self):
        self.assertIsNotNone(monitor_cli_commands.write_default_config)
        self.assertIsNotNone(monitor_cli_commands.export_feedback)
        self.assertIsNotNone(monitor_cli_commands.test_telegram_bot)
        self.assertEqual(monitor_runner.write_default_config.__name__, "write_default_config")
        self.assertEqual(monitor_runner.export_feedback.__name__, "export_feedback")
        self.assertEqual(monitor_runner.test_telegram_bot.__name__, "test_telegram_bot")


    def test_write_default_config_respects_monitor_project_root_patch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdout = io.StringIO()
            args = Namespace(config=".tgcs/profiles.toml", force=True, format="json")

            with patch.object(monitor, "PROJECT_ROOT", root):
                with patch("sys.stdout", stdout):
                    exit_code = monitor.write_default_config(args)

            payload = json.loads(stdout.getvalue())
            config_path = root / ".tgcs" / "profiles.toml"
            config_text = config_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, agent_cli.EXIT_SUCCESS)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["config_path"], ".tgcs/profiles.toml")
        self.assertIn("schema_version = \"profile_run_config_v1\"", config_text)
        self.assertIn("scan_concurrency = 3", config_text)
        self.assertIn("semantic_batch_size = 20", config_text)


    def test_telegram_bot_missing_chat_id_does_not_send_delivery(self):
        stdout = io.StringIO()
        args = Namespace(
            chat_id="",
            target_id="telegram-bot-default",
            delivery_mode="dry-run",
            format="json",
        )

        with patch.object(monitor_cli_commands.delivery, "send_telegram_bot_message") as send_mock:
            with patch("sys.stdout", stdout):
                exit_code = monitor.test_telegram_bot(args)

        payload = json.loads(stdout.getvalue())
        send_mock.assert_not_called()
        self.assertEqual(exit_code, agent_cli.EXIT_VALIDATION)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "telegram_bot_chat_id_missing")


    def test_monitor_runner_wrappers_preserve_legacy_patch_surface(self):
        class FakeAttempt:
            ok = True
            status = "dry_run"

            @staticmethod
            def to_dict():
                return {"status": "dry_run"}

        stdout = io.StringIO()
        args = Namespace(
            chat_id="12345",
            target_id="telegram-bot-default",
            delivery_mode="dry-run",
            format="json",
        )

        with patch.object(monitor_runner.delivery, "send_telegram_bot_message", return_value=FakeAttempt()) as send_mock:
            with patch("sys.stdout", stdout):
                exit_code = monitor_runner.test_telegram_bot(args)

        payload = json.loads(stdout.getvalue())
        send_mock.assert_called_once_with(
            target_id="telegram-bot-default",
            chat_id="12345",
            text="T-Sense delivery test.",
            mode="dry-run",
        )
        self.assertEqual(exit_code, agent_cli.EXIT_SUCCESS)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["attempt"]["status"], "dry_run")


    def test_monitor_runner_write_default_config_preserves_schema_constant_patch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            args = Namespace(config=".tgcs/profiles.toml", force=True, format="json")
            stdout = io.StringIO()

            with patch.object(monitor_runner, "PROFILE_RUN_CONFIG_SCHEMA_VERSION", "patched_schema_v1"):
                with patch.object(monitor_runner, "root_path", side_effect=lambda value: root / value):
                    with patch.object(
                        monitor_runner,
                        "relative_to_root",
                        side_effect=lambda path: str(Path(path).relative_to(root)).replace("\\", "/"),
                    ):
                        with patch("sys.stdout", stdout):
                            exit_code = monitor_runner.write_default_config(args)

            payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, agent_cli.EXIT_SUCCESS)
        self.assertEqual(payload["data"]["schema_version"], "patched_schema_v1")
        self.assertEqual(payload["data"]["config_path"], ".tgcs/profiles.toml")


if __name__ == "__main__":
    unittest.main()
