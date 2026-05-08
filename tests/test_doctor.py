import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class DoctorTests(unittest.TestCase):
    def test_json_reports_missing_credentials_as_failure(self):
        from scripts import doctor

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            channel_list = root / "channels.txt"
            profile = root / "profile.md"
            output_dir = root / "output"
            channel_list.write_text("remote_jobs\n", encoding="utf-8")
            profile.write_text("# Profile\n\n## Basic Info\n- **Role**: Frontend\n", encoding="utf-8")
            stdout = io.StringIO()

            with patch.dict("os.environ", {}, clear=True):
                with patch("sys.stdout", stdout):
                    exit_code = doctor.main(
                        [
                            "--channel-list",
                            str(channel_list),
                            "--profile",
                            str(profile),
                            "--output-dir",
                            str(output_dir),
                            "--config-path",
                            str(root / "missing.toml"),
                            "--session-path",
                            str(root / "missing.session"),
                            "--json",
                        ]
                    )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["summary"]["fail"], 1)
        self.assertEqual(payload["checks"]["telegram_credentials"]["status"], "fail")

    def test_env_credentials_pass_and_missing_session_is_warning_only(self):
        from scripts import doctor

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            channel_list = root / "channels.txt"
            profile = root / "profile.md"
            channel_list.write_text("remote_jobs\n", encoding="utf-8")
            profile.write_text("# Profile\n\n## Basic Info\n- **Role**: Frontend\n", encoding="utf-8")
            stdout = io.StringIO()

            with patch.dict(
                "os.environ",
                {"TELEGRAM_API_ID": "123", "TELEGRAM_API_HASH": "hash", "OPENAI_API_KEY": "sk-test"},
                clear=True,
            ):
                with patch("sys.stdout", stdout):
                    exit_code = doctor.main(
                        [
                            "--channel-list",
                            str(channel_list),
                            "--profile",
                            str(profile),
                            "--output-dir",
                            str(root / "output"),
                            "--config-path",
                            str(root / "missing.toml"),
                            "--session-path",
                            str(root / "missing.session"),
                            "--json",
                        ]
                    )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["checks"]["telegram_credentials"]["status"], "pass")
        self.assertEqual(payload["checks"]["telegram_session"]["status"], "warn")
        self.assertEqual(payload["checks"]["llm_provider"]["status"], "pass")

    def test_empty_channel_list_and_output_file_are_failures(self):
        from scripts import doctor

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            channel_list = root / "channels.txt"
            profile = root / "profile.md"
            output_file = root / "output-as-file"
            channel_list.write_text("\n# nothing here\n", encoding="utf-8")
            profile.write_text("# Profile\n\n## Basic Info\n- **Role**: Frontend\n", encoding="utf-8")
            output_file.write_text("not a directory", encoding="utf-8")
            stdout = io.StringIO()

            with patch.dict(
                "os.environ",
                {"TELEGRAM_API_ID": "123", "TELEGRAM_API_HASH": "hash"},
                clear=True,
            ):
                with patch("sys.stdout", stdout):
                    exit_code = doctor.main(
                        [
                            "--channel-list",
                            str(channel_list),
                            "--profile",
                            str(profile),
                            "--output-dir",
                            str(output_file),
                            "--config-path",
                            str(root / "missing.toml"),
                            "--session-path",
                            str(root / "missing.session"),
                            "--json",
                        ]
                    )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["checks"]["channel_list"]["status"], "fail")
        self.assertEqual(payload["checks"]["output_directory"]["status"], "fail")

    def test_online_telegram_check_is_explicit_and_non_interactive(self):
        from scripts import doctor

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            channel_list = root / "channels.txt"
            profile = root / "profile.md"
            channel_list.write_text("remote_jobs\n", encoding="utf-8")
            profile.write_text("# Profile\n\n## Basic Info\n- **Role**: Frontend\n", encoding="utf-8")
            stdout = io.StringIO()

            with patch.dict(
                "os.environ",
                {"TELEGRAM_API_ID": "123", "TELEGRAM_API_HASH": "hash"},
                clear=True,
            ):
                with patch.object(
                    doctor,
                    "check_online_telegram",
                    return_value=doctor.CheckResult(
                        "telegram_online", "warn", "session is not authorized"
                    ),
                ) as online:
                    with patch("builtins.input", side_effect=AssertionError("doctor must not prompt")):
                        with patch("sys.stdout", stdout):
                            exit_code = doctor.main(
                                [
                                    "--channel-list",
                                    str(channel_list),
                                    "--profile",
                                    str(profile),
                                    "--output-dir",
                                    str(root / "output"),
                                    "--config-path",
                                    str(root / "missing.toml"),
                                    "--session-path",
                                    str(root / "session"),
                                    "--online-telegram",
                                    "--json",
                                ]
                            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        online.assert_called_once()
        self.assertEqual(payload["checks"]["telegram_online"]["status"], "warn")


if __name__ == "__main__":
    unittest.main()
