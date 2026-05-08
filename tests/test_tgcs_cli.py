import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def load_tgcs_module(testcase):
    try:
        from scripts import tgcs
    except ModuleNotFoundError as exc:
        testcase.fail(f"scripts.tgcs should exist: {exc}")
    return tgcs


class TgcsCliTests(unittest.TestCase):
    def test_run_defaults_to_market_news_html_registry_and_state(self):
        tgcs = load_tgcs_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".tgcs").mkdir()
            (root / ".tgcs" / "sources.json").write_text("{}", encoding="utf-8")
            calls = []

            def fake_run(cmd, check=False):
                calls.append(cmd)
                return subprocess.CompletedProcess(cmd, 0)

            with patch.object(tgcs, "PROJECT_ROOT", root):
                with patch.object(tgcs.subprocess, "run", side_effect=fake_run):
                    exit_code = tgcs.main(["run"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(calls), 1)
        cmd = [str(part) for part in calls[0]]
        self.assertIn("daily_report.py", cmd[1])
        self.assertIn("--source-registry", cmd)
        self.assertIn(str(root / ".tgcs" / "sources.json"), cmd)
        self.assertIn("--profile", cmd)
        self.assertIn(str(root / "profiles" / "templates" / "market-news.md"), cmd)
        self.assertIn("--html", cmd)
        self.assertIn("--state-dir", cmd)
        self.assertIn(str(root / ".tgcs" / "state"), cmd)

    def test_run_no_state_omits_state_dir(self):
        tgcs = load_tgcs_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".tgcs").mkdir()
            (root / ".tgcs" / "sources.json").write_text("{}", encoding="utf-8")

            def fake_run(cmd, check=False):
                return subprocess.CompletedProcess(cmd, 0)

            with patch.object(tgcs, "PROJECT_ROOT", root):
                with patch.object(tgcs.subprocess, "run", side_effect=fake_run) as run_mock:
                    exit_code = tgcs.main(["run", "--no-state"])

        self.assertEqual(exit_code, 0)
        cmd = [str(part) for part in run_mock.call_args.args[0]]
        self.assertNotIn("--state-dir", cmd)

    def test_demo_uses_offline_fixture_defaults(self):
        tgcs = load_tgcs_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fake_run(cmd, check=False):
                return subprocess.CompletedProcess(cmd, 0)

            with patch.object(tgcs, "PROJECT_ROOT", root):
                with patch.object(tgcs.subprocess, "run", side_effect=fake_run) as run_mock:
                    exit_code = tgcs.main(["demo"])

        self.assertEqual(exit_code, 0)
        cmd = [str(part) for part in run_mock.call_args.args[0]]
        self.assertIn("report.py", cmd[1])
        self.assertIn("--html-only", cmd)
        self.assertIn(str(root / "docs" / "demo" / "fixtures" / "demo-report.md"), cmd)
        self.assertIn(str(root / "output" / "demo-report.md"), cmd)

    def test_init_creates_local_config_and_source_registry(self):
        tgcs = load_tgcs_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "channel_lists").mkdir()
            (root / "channel_lists" / "example.txt").write_text("example\n", encoding="utf-8")

            def fake_run(cmd, check=False):
                return subprocess.CompletedProcess(cmd, 0)

            with patch.object(tgcs, "PROJECT_ROOT", root):
                with patch.object(tgcs.subprocess, "run", side_effect=fake_run) as run_mock:
                    exit_code = tgcs.main(["init"])

            config_text = (root / ".tgcs" / "config.toml").read_text(encoding="utf-8")
            profiles_config_text = (root / ".tgcs" / "profiles.toml").read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn("profile", config_text)
        self.assertIn("state_dir", config_text)
        self.assertIn("profile_run_config_v1", profiles_config_text)
        cmd = [str(part) for part in run_mock.call_args.args[0]]
        self.assertIn("source_registry.py", cmd[1])
        self.assertIn("import-list", cmd)

    def test_login_calls_scan_login_only(self):
        tgcs = load_tgcs_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fake_run(cmd, check=False):
                return subprocess.CompletedProcess(cmd, 0)

            with patch.object(tgcs, "PROJECT_ROOT", root):
                with patch.object(tgcs.subprocess, "run", side_effect=fake_run) as run_mock:
                    exit_code = tgcs.main(["login"])

        self.assertEqual(exit_code, 0)
        cmd = [str(part) for part in run_mock.call_args.args[0]]
        self.assertIn("scan.py", cmd[1])
        self.assertIn("--login-only", cmd)

    def test_monitor_run_delegates_to_monitor_script(self):
        tgcs = load_tgcs_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fake_run(cmd, check=False):
                return subprocess.CompletedProcess(cmd, 0)

            with patch.object(tgcs, "PROJECT_ROOT", root):
                with patch.object(tgcs.subprocess, "run", side_effect=fake_run) as run_mock:
                    exit_code = tgcs.main(
                        [
                            "monitor",
                            "run",
                            "--profile-id",
                            "market-news",
                            "--delivery-mode",
                            "dry-run",
                            "--format",
                            "json",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        cmd = [str(part) for part in run_mock.call_args.args[0]]
        self.assertIn("monitor.py", cmd[1])
        self.assertIn("run", cmd)
        self.assertIn("--profile-id", cmd)
        self.assertIn("market-news", cmd)
        self.assertIn("--format", cmd)

    def test_dashboard_delegates_to_dashboard_server(self):
        tgcs = load_tgcs_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fake_run(cmd, check=False):
                return subprocess.CompletedProcess(cmd, 0)

            with patch.object(tgcs, "PROJECT_ROOT", root):
                with patch.object(tgcs.subprocess, "run", side_effect=fake_run) as run_mock:
                    exit_code = tgcs.main(["dashboard", "--port", "8765"])

        self.assertEqual(exit_code, 0)
        cmd = [str(part) for part in run_mock.call_args.args[0]]
        self.assertIn("dashboard_server.py", cmd[1])
        self.assertIn("--host", cmd)
        self.assertIn("127.0.0.1", cmd)

    def test_delivery_test_delegates_to_monitor_delivery_test(self):
        tgcs = load_tgcs_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def fake_run(cmd, check=False):
                return subprocess.CompletedProcess(cmd, 0)

            with patch.object(tgcs, "PROJECT_ROOT", root):
                with patch.object(tgcs.subprocess, "run", side_effect=fake_run) as run_mock:
                    exit_code = tgcs.main(["delivery", "test", "telegram-bot", "--chat-id", "123"])

        self.assertEqual(exit_code, 0)
        cmd = [str(part) for part in run_mock.call_args.args[0]]
        self.assertIn("monitor.py", cmd[1])
        self.assertIn("delivery-test", cmd)
        self.assertIn("telegram-bot", cmd)


if __name__ == "__main__":
    unittest.main()
