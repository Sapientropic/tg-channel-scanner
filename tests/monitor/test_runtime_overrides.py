import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import monitor, monitor_state


class MonitorRuntimeOverrideTests(unittest.TestCase):
    def test_desk_delivery_target_override_applies_to_loaded_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / ".tgcs" / "tgcs.db"
            config = monitor.default_config(root / ".tgcs" / "profiles.toml")
            conn = monitor_state.connect(db_path)
            try:
                monitor_state.upsert_delivery_target(
                    conn,
                    {
                        "id": "telegram-bot-default",
                        "type": "telegram_bot",
                        "enabled": True,
                        "chat_id": "@desk_signal",
                        "bot_token": "secret-token",
                    },
                )
                updated = monitor.apply_delivery_runtime_overrides(conn, config)
            finally:
                conn.close()

        target = updated.delivery_targets["telegram-bot-default"]
        self.assertTrue(target["enabled"])
        self.assertEqual(target["chat_id"], "@desk_signal")
        self.assertNotIn("bot_token", target)

    def test_desk_delivery_target_override_wins_over_file_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / ".tgcs" / "tgcs.db"
            config = monitor.MonitorConfig(
                path=root / ".tgcs" / "profiles.toml",
                profiles={},
                delivery_targets={
                    "telegram-bot-default": {
                        "id": "telegram-bot-default",
                        "type": "telegram_bot",
                        "enabled": False,
                        "chat_id": "toml-default",
                    }
                },
                defaults={},
            )
            conn = monitor_state.connect(db_path)
            try:
                monitor_state.upsert_delivery_target(
                    conn,
                    {
                        "id": "telegram-bot-default",
                        "type": "telegram_bot",
                        "enabled": True,
                        "chat_id": "desk-override",
                    },
                )
                updated = monitor.apply_delivery_runtime_overrides(conn, config)
            finally:
                conn.close()

        target = updated.delivery_targets["telegram-bot-default"]
        self.assertTrue(target["enabled"])
        self.assertEqual(target["chat_id"], "desk-override")

    def test_monitor_run_preserves_desk_delivery_target_override_after_writeback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_path = root / "profiles" / "templates" / "market-news.md"
            profile_path.parent.mkdir(parents=True)
            profile_path.write_text("# Profile\n\n## Basic Info\n- **Role**: Market\n", encoding="utf-8")
            config_path = root / ".tgcs" / "profiles.toml"
            db_path = root / ".tgcs" / "tgcs.db"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                "\n".join(
                    [
                        'schema_version = "profile_run_config_v1"',
                        "",
                        "[[profiles]]",
                        'id = "market-news"',
                        'path = "profiles/templates/market-news.md"',
                        "enabled = true",
                        'alert_schedule_mode = "muted"',
                        'delivery_targets = ["telegram-bot-default"]',
                        "",
                        "[[delivery]]",
                        'id = "telegram-bot-default"',
                        'type = "telegram_bot"',
                        "enabled = false",
                        'chat_id = "toml-default"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            scan = root / "scan.jsonl"
            scan.write_text(
                json.dumps({"channel": "market", "id": 7, "date": "2026-05-08T08:30:00Z"}) + "\n",
                encoding="utf-8",
            )
            output_dir = root / "output"
            conn = monitor_state.connect(db_path)
            try:
                monitor_state.upsert_delivery_target(
                    conn,
                    {
                        "id": "telegram-bot-default",
                        "type": "telegram_bot",
                        "enabled": True,
                        "chat_id": "desk-override",
                    },
                )
            finally:
                conn.close()

            def fake_run_json_command(cmd):
                run_dir = output_dir / "runs" / "run-delivery-target"
                report_path = run_dir / "report.md"
                html_path = run_dir / "report.html"
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text("# Report", encoding="utf-8")
                html_path.write_text("<html></html>", encoding="utf-8")
                return (
                    0,
                    {
                        "ok": True,
                        "data": {
                            "status": "complete",
                            "report_path": str(report_path),
                            "html_path": str(html_path),
                            "items": [],
                        },
                    },
                    "",
                )

            stdout = io.StringIO()
            with patch.object(monitor, "PROJECT_ROOT", root):
                with patch.object(monitor, "run_json_command", side_effect=fake_run_json_command):
                    with patch("sys.stdout", stdout):
                        exit_code = monitor.main(
                            [
                                "run",
                                "--profile-id",
                                "market-news",
                                "--run-id",
                                "run-delivery-target",
                                "--config",
                                str(config_path),
                                "--scan-input",
                                str(scan),
                                "--output-dir",
                                str(output_dir),
                                "--db",
                                str(db_path),
                                "--delivery-mode",
                                "dry-run",
                                "--format",
                                "json",
                            ]
                        )
            conn = monitor_state.connect(db_path)
            try:
                snapshot = monitor_state.dashboard_snapshot(conn)
            finally:
                conn.close()

        self.assertEqual(exit_code, 0)
        target = snapshot["delivery_targets"][0]
        self.assertTrue(target["enabled"])
        self.assertEqual(target["config"]["chat_id"], "desk-override")

    def test_dashboard_alert_mode_override_applies_to_next_monitor_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_path = root / "profiles" / "templates" / "market-news.md"
            profile_path.parent.mkdir(parents=True)
            profile_path.write_text("# Profile\n\n## Basic Info\n- **Role**: Market\n", encoding="utf-8")
            config_path = root / ".tgcs" / "profiles.toml"
            db_path = root / ".tgcs" / "tgcs.db"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                "\n".join(
                    [
                        'schema_version = "profile_run_config_v1"',
                        "",
                        "[[profiles]]",
                        'id = "market-news"',
                        'path = "profiles/templates/market-news.md"',
                        "enabled = true",
                        'alert_schedule_mode = "all_day"',
                        'delivery_targets = ["telegram-bot-default"]',
                        "",
                        "[[delivery]]",
                        'id = "telegram-bot-default"',
                        'type = "telegram_bot"',
                        "enabled = true",
                        'chat_id = "123"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            scan = root / "scan.jsonl"
            scan.write_text(
                json.dumps({"channel": "market", "id": 7, "date": "2026-05-08T08:30:00Z"}) + "\n",
                encoding="utf-8",
            )
            output_dir = root / "output"
            conn = monitor_state.connect(db_path)
            try:
                monitor_state.upsert_profile(
                    conn,
                    {
                        "id": "market-news",
                        "path": str(profile_path),
                        "enabled": True,
                        "alert_schedule_mode": "muted",
                    },
                )
            finally:
                conn.close()

            def fake_run_json_command(cmd):
                run_dir = output_dir / "runs" / "run-muted"
                report_path = run_dir / "report.md"
                html_path = run_dir / "report.html"
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text("# Report", encoding="utf-8")
                html_path.write_text("<html></html>", encoding="utf-8")
                return (
                    0,
                    {
                        "ok": True,
                        "data": {
                            "status": "complete",
                            "report_path": str(report_path),
                            "html_path": str(html_path),
                            "diagnostics": [
                                {
                                    "code": "scan_incomplete",
                                    "severity": "warning",
                                    "message": "One source may be incomplete.",
                                    "next_step": "Rerun with a narrower scan window.",
                                }
                            ],
                            "items": [
                                {
                                    "topic": "Urgent market lead",
                                    "rating": "high",
                                    "why": "Decision relevant.",
                                    "decision_state": {"status": "new", "semantic_cluster": "lead-1"},
                                    "source_message_refs": [{"channel": "market", "id": 7}],
                                }
                            ],
                        },
                    },
                    "",
                )

            stdout = io.StringIO()
            with patch.object(monitor, "PROJECT_ROOT", root):
                with patch.object(monitor, "run_json_command", side_effect=fake_run_json_command):
                    with patch("sys.stdout", stdout):
                        exit_code = monitor.main(
                            [
                                "run",
                                "--profile-id",
                                "market-news",
                                "--run-id",
                                "run-muted",
                                "--config",
                                str(config_path),
                                "--scan-input",
                                str(scan),
                                "--output-dir",
                                str(output_dir),
                                "--db",
                                str(db_path),
                                "--delivery-mode",
                                "dry-run",
                                "--format",
                                "json",
                            ]
                        )

            payload = json.loads(stdout.getvalue())
            manifest = json.loads((output_dir / "runs" / "run-muted" / "run-manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["alert_count"], 1)
        self.assertEqual(payload["data"]["delivery_attempts"], [])
        self.assertEqual(manifest["alert_schedule"]["mode"], "muted")
        self.assertFalse(manifest["alert_schedule"]["delivery_enabled"])
        self.assertEqual(manifest["alert_schedule"]["suppressed_reason"], "muted")

    def test_dashboard_enabled_override_blocks_next_monitor_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_path = root / "profiles" / "templates" / "market-news.md"
            profile_path.parent.mkdir(parents=True)
            profile_path.write_text("# Profile\n\n## Basic Info\n- **Role**: Market\n", encoding="utf-8")
            config_path = root / ".tgcs" / "profiles.toml"
            db_path = root / ".tgcs" / "tgcs.db"
            output_dir = root / "output"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                "\n".join(
                    [
                        'schema_version = "profile_run_config_v1"',
                        "",
                        "[[profiles]]",
                        'id = "market-news"',
                        'path = "profiles/templates/market-news.md"',
                        "enabled = true",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            conn = monitor_state.connect(db_path)
            try:
                monitor_state.upsert_profile(
                    conn,
                    {
                        "id": "market-news",
                        "path": "profiles/templates/market-news.md",
                        "enabled": False,
                    },
                )
            finally:
                conn.close()

            stdout = io.StringIO()
            with patch.object(monitor, "PROJECT_ROOT", root):
                with patch("sys.stdout", stdout):
                    exit_code = monitor.main(
                        [
                            "run",
                            "--profile-id",
                            "market-news",
                            "--run-id",
                            "run-disabled",
                            "--config",
                            str(config_path),
                            "--output-dir",
                            str(output_dir),
                            "--db",
                            str(db_path),
                            "--delivery-mode",
                            "dry-run",
                            "--format",
                            "json",
                        ]
                    )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, monitor.agent_cli.EXIT_VALIDATION)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "profile_disabled")
        self.assertTrue(payload["error"]["retryable"])
        self.assertIn("Enable the profile in Signal Desk Profiles", payload["error"]["next_step"])
        self.assertFalse((output_dir / "runs" / "run-disabled").exists())

    def test_dashboard_runtime_settings_override_next_monitor_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_path = root / "profiles" / "templates" / "market-news.md"
            profile_path.parent.mkdir(parents=True)
            profile_path.write_text("# Profile\n\n## Basic Info\n- **Role**: Market\n", encoding="utf-8")
            config_path = root / ".tgcs" / "profiles.toml"
            db_path = root / ".tgcs" / "tgcs.db"
            output_dir = root / "output"
            config_path.parent.mkdir(parents=True)
            config_path.write_text(
                "\n".join(
                    [
                        'schema_version = "profile_run_config_v1"',
                        "",
                        "[[profiles]]",
                        'id = "market-news"',
                        'path = "profiles/templates/market-news.md"',
                        "enabled = true",
                        "scan_window_hours = 2",
                        "semantic_max_messages = 20",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            scan = root / "scan.jsonl"
            scan.write_text(
                json.dumps({"channel": "market", "id": 7, "date": "2026-05-08T08:30:00Z"}) + "\n",
                encoding="utf-8",
            )
            conn = monitor_state.connect(db_path)
            try:
                monitor_state.upsert_profile(
                    conn,
                    {
                        "id": "market-news",
                        "path": "profiles/templates/market-news.md",
                        "enabled": True,
                        "scan_window_hours": 6,
                        "semantic_max_messages": 40,
                    },
                )
            finally:
                conn.close()

            def fake_run_json_command(cmd):
                run_dir = output_dir / "runs" / "run-runtime-settings"
                report_path = run_dir / "report.md"
                html_path = run_dir / "report.html"
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text("# Report", encoding="utf-8")
                html_path.write_text("<html></html>", encoding="utf-8")
                return (
                    0,
                    {
                        "ok": True,
                        "data": {
                            "status": "complete",
                            "report_path": str(report_path),
                            "html_path": str(html_path),
                            "diagnostics": [],
                            "items": [],
                        },
                    },
                    "",
                )

            stdout = io.StringIO()
            with patch.object(monitor, "PROJECT_ROOT", root):
                with patch.object(monitor, "run_json_command", side_effect=fake_run_json_command):
                    with patch("sys.stdout", stdout):
                        exit_code = monitor.main(
                            [
                                "run",
                                "--profile-id",
                                "market-news",
                                "--run-id",
                                "run-runtime-settings",
                                "--config",
                                str(config_path),
                                "--scan-input",
                                str(scan),
                                "--output-dir",
                                str(output_dir),
                                "--db",
                                str(db_path),
                                "--delivery-mode",
                                "dry-run",
                                "--format",
                                "json",
                            ]
                        )

            manifest = json.loads((output_dir / "runs" / "run-runtime-settings" / "run-manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertEqual(manifest["scan_window"]["hours"], 6)
        self.assertEqual(manifest["semantic"]["max_messages"], 40)



if __name__ == "__main__":
    unittest.main()
