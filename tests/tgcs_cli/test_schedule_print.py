import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.tgcs_cli import load_tgcs_module


class TgcsSchedulePrintTests(unittest.TestCase):
    def test_schedule_print_windows_outputs_task_scheduler_command_without_running_it(self):
        tgcs = load_tgcs_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdout = io.StringIO()
            with patch.object(tgcs, "PROJECT_ROOT", root):
                with patch.object(tgcs.subprocess, "run") as run_mock:
                    with patch("sys.stdout", stdout):
                        exit_code = tgcs.main(
                            [
                                "schedule",
                                "print",
                                "--platform",
                                "windows",
                                "--profile-id",
                                "jobs-fast",
                                "--interval-minutes",
                                "15",
                                "--delivery-mode",
                                "live",
                            ]
                        )

        self.assertEqual(exit_code, 0)
        run_mock.assert_not_called()
        output = stdout.getvalue()
        self.assertIn("schtasks", output)
        self.assertIn("tgcs.bat", output)
        self.assertIn("jobs-fast", output)
        self.assertIn("--delivery-mode live", output)

    def test_schedule_print_uses_profile_work_interval_when_not_overridden(self):
        tgcs = load_tgcs_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".tgcs").mkdir()
            (root / ".tgcs" / "profiles.toml").write_text(
                "\n".join(
                    [
                        'schema_version = "profile_run_config_v1"',
                        "",
                        "[[profiles]]",
                        'id = "jobs-fast"',
                        'path = "profiles/templates/jobs.md"',
                        "work_interval_minutes = 17",
                        "",
                        "[[profiles]]",
                        'id = "market-news"',
                        'path = "profiles/templates/market-news.md"',
                        "work_interval_minutes = 120",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with patch.object(tgcs, "PROJECT_ROOT", root):
                with patch.object(tgcs.subprocess, "run") as run_mock:
                    with patch("sys.stdout", stdout):
                        exit_code = tgcs.main(["schedule", "print", "--platform", "windows", "--profile-id", "jobs-fast"])

        self.assertEqual(exit_code, 0)
        run_mock.assert_not_called()
        self.assertIn("/MO 17", stdout.getvalue())

    def test_schedule_print_explicit_interval_overrides_profile_interval(self):
        tgcs = load_tgcs_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".tgcs").mkdir()
            (root / ".tgcs" / "profiles.toml").write_text(
                "\n".join(
                    [
                        'schema_version = "profile_run_config_v1"',
                        "",
                        "[[profiles]]",
                        'id = "jobs-fast"',
                        'path = "profiles/templates/jobs.md"',
                        "work_interval_minutes = 17",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            with patch.object(tgcs, "PROJECT_ROOT", root):
                with patch("sys.stdout", stdout):
                    exit_code = tgcs.main(
                        [
                            "schedule",
                            "print",
                            "--platform",
                            "cron",
                            "--profile-id",
                            "jobs-fast",
                            "--interval-minutes",
                            "30",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        self.assertIn("*/30 * * * *", stdout.getvalue())
        self.assertNotIn("*/17", stdout.getvalue())

    def test_schedule_print_unknown_profile_fails_clearly(self):
        tgcs = load_tgcs_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdout = io.StringIO()
            with patch.object(tgcs, "PROJECT_ROOT", root):
                with patch("sys.stdout", stdout):
                    with self.assertRaises(SystemExit) as raised:
                        tgcs.main(["schedule", "print", "--platform", "windows", "--profile-id", "missing"])

        self.assertIn("Profile id not found: missing", str(raised.exception))

    def test_schedule_print_windows_quotes_tgcs_path_inside_task_action(self):
        tgcs = load_tgcs_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "with space"
            stdout = io.StringIO()
            with patch.object(tgcs, "PROJECT_ROOT", root):
                with patch("sys.stdout", stdout):
                    exit_code = tgcs.main(["schedule", "print", "--platform", "windows"])

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn(f'\\"{root / "tgcs.bat"}\\" monitor run', output)

    def test_schedule_print_cron_outputs_crontab_line_without_running_it(self):
        tgcs = load_tgcs_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdout = io.StringIO()
            with patch.object(tgcs, "PROJECT_ROOT", root):
                with patch.object(tgcs.subprocess, "run") as run_mock:
                    with patch("sys.stdout", stdout):
                        exit_code = tgcs.main(
                            [
                                "schedule",
                                "print",
                                "--platform",
                                "cron",
                                "--profile-id",
                                "jobs-fast",
                                "--interval-minutes",
                                "15",
                            ]
                        )

        self.assertEqual(exit_code, 0)
        run_mock.assert_not_called()
        output = stdout.getvalue()
        self.assertIn("*/15 * * * *", output)
        self.assertIn("./tgcs monitor run --profile-id jobs-fast", output)

    def test_schedule_print_launchd_outputs_launch_agent_preview_without_running_it(self):
        tgcs = load_tgcs_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdout = io.StringIO()
            with patch.object(tgcs, "PROJECT_ROOT", root):
                with patch.object(tgcs.subprocess, "run") as run_mock:
                    with patch("sys.stdout", stdout):
                        exit_code = tgcs.main(
                            [
                                "schedule",
                                "print",
                                "--platform",
                                "launchd",
                                "--profile-id",
                                "jobs-fast",
                                "--interval-minutes",
                                "15",
                            ]
                        )

        self.assertEqual(exit_code, 0)
        run_mock.assert_not_called()
        output = stdout.getvalue()
        self.assertIn("LaunchAgent plist path:", output)
        self.assertIn("com.sapientropic.tgcs.jobs-fast.dry-run.plist", output)
        self.assertIn(str(root / "tgcs"), output)
        self.assertIn("launchctl load -w", output)

    def test_schedule_print_systemd_outputs_user_timer_preview_without_running_it(self):
        tgcs = load_tgcs_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdout = io.StringIO()
            with patch.object(tgcs, "PROJECT_ROOT", root):
                with patch.object(tgcs.subprocess, "run") as run_mock:
                    with patch("sys.stdout", stdout):
                        exit_code = tgcs.main(
                            [
                                "schedule",
                                "print",
                                "--platform",
                                "systemd",
                                "--profile-id",
                                "jobs-fast",
                                "--interval-minutes",
                                "15",
                            ]
                        )

        self.assertEqual(exit_code, 0)
        run_mock.assert_not_called()
        output = stdout.getvalue()
        self.assertIn("systemd user service:", output)
        self.assertIn("tgcs-jobs-fast-dry-run.service", output)
        self.assertIn("systemctl --user enable --now tgcs-jobs-fast-dry-run.timer", output)
        self.assertIn(str(root / "tgcs"), output)

    def test_schedule_print_auto_uses_cron_when_linux_user_runtime_is_missing(self):
        tgcs = load_tgcs_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdout = io.StringIO()
            with patch.object(tgcs, "PROJECT_ROOT", root):
                with patch.object(tgcs.sys, "platform", "linux"):
                    with patch.object(tgcs.shutil, "which", return_value="/usr/bin/systemctl"):
                        with patch.dict(tgcs.os.environ, {"XDG_RUNTIME_DIR": ""}, clear=False):
                            with patch("sys.stdout", stdout):
                                exit_code = tgcs.main(
                                    [
                                        "schedule",
                                        "print",
                                        "--platform",
                                        "auto",
                                        "--profile-id",
                                        "jobs-fast",
                                        "--interval-minutes",
                                        "15",
                                    ]
                                )

        self.assertEqual(exit_code, 0)
        output = stdout.getvalue()
        self.assertIn("Crontab line:", output)
        self.assertIn("*/15 * * * *", output)
        self.assertNotIn("systemd user service:", output)

    def test_schedule_print_cron_outputs_two_hour_interval(self):
        tgcs = load_tgcs_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdout = io.StringIO()
            with patch.object(tgcs, "PROJECT_ROOT", root):
                with patch("sys.stdout", stdout):
                    exit_code = tgcs.main(
                        [
                            "schedule",
                            "print",
                            "--platform",
                            "cron",
                            "--profile-id",
                            "market-news",
                            "--interval-minutes",
                            "120",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        self.assertIn("0 */2 * * *", stdout.getvalue())



if __name__ == "__main__":
    unittest.main()
