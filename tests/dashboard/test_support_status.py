import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import dashboard_server, desk_support


class DashboardSupportStatusTests(unittest.TestCase):
    def test_support_status_reports_state_paths_without_secret_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "Application Support" / "T-Sense"
            code_root = root / "bundle-code"
            log_path = root / "Logs" / "T-Sense" / "desktop-backend.log"
            telegram_dir = state_root / ".tgcs" / "telegram"
            state_root.mkdir(parents=True)
            telegram_dir.mkdir(parents=True)
            log_path.parent.mkdir(parents=True)
            log_path.write_text("token=123456:SECRET-SHOULD-STAY-IN-FILE\n", encoding="utf-8")

            status = desk_support.desk_support_status(
                project_root=state_root,
                code_root=code_root,
                db_path=state_root / ".tgcs" / "tgcs.db",
                telegram_config_dir=telegram_dir,
                dashboard_url="http://127.0.0.1:8766",
                desktop_log_path=log_path,
                legacy_telegram_config_dir=root / ".config" / "tgcli",
                now_fn=lambda: "2026-05-16T14:00:00Z",
            )

        rendered = str(status)
        self.assertEqual(status["schema_version"], "desk_support_status_v1")
        self.assertEqual(status["app_data_root"], str(state_root))
        self.assertEqual(status["desktop_log_path"], str(log_path))
        self.assertEqual(status["migration"]["status"], "no_legacy_data")
        self.assertEqual(status["migration"]["legacy_locations"], [])
        path_targets = {item["label"]: item.get("target") for item in status["paths"]}
        self.assertEqual(path_targets["Local data"], "app_data_root")
        self.assertEqual(path_targets["Reports"], "output_dir")
        self.assertEqual(path_targets["Backend log"], "desktop_log")
        self.assertEqual(path_targets["Telegram session"], "telegram_config")
        self.assertTrue(any(item["label"] == "Local data" and item["exists"] for item in status["paths"]))
        self.assertTrue(any(item["label"] == "AI requests" and item["external"] for item in status["data_boundaries"]))
        self.assertIn("Backend will not start", [item["label"] for item in status["recovery"]])
        self.assertNotIn("123456:SECRET", rendered)


    def test_support_diagnostic_export_writes_secret_free_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "Application Support" / "T-Sense"
            code_root = root / "bundle-code"
            log_path = root / "Logs" / "T-Sense" / "desktop-backend.log"
            telegram_dir = state_root / ".tgcs" / "telegram"
            report_path = state_root / "output" / "demo-report.html"
            telegram_dir.mkdir(parents=True)
            log_path.parent.mkdir(parents=True)
            report_path.parent.mkdir(parents=True)
            log_path.write_text("token=123456:SECRET-SHOULD-STAY-IN-FILE\n", encoding="utf-8")
            report_path.write_text("raw private Telegram message should stay in report\n", encoding="utf-8")

            result = desk_support.write_support_diagnostic_export(
                project_root=state_root,
                code_root=code_root,
                db_path=state_root / ".tgcs" / "tgcs.db",
                telegram_config_dir=telegram_dir,
                dashboard_url="http://127.0.0.1:8766",
                desktop_log_path=log_path,
                legacy_telegram_config_dir=root / ".config" / "tgcli",
                now_fn=lambda: "2026-05-16T14:00:00Z",
            )

            output_path = Path(result["output_path"])
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            rendered = output_path.read_text(encoding="utf-8")
            self.assertEqual(result["schema_version"], "desk_support_diagnostic_export_v1")
            self.assertEqual(payload["schema_version"], "desk_support_diagnostic_export_v1")
            self.assertEqual(payload["exported_at"], "2026-05-16T14:00:00Z")
            self.assertEqual(payload["status"]["schema_version"], "desk_support_status_v1")
            self.assertTrue(output_path.name.startswith("t-sense-support-"))
            self.assertIn("raw private text", " ".join(item["label"] for item in payload["excluded"]))
            self.assertNotIn("123456:SECRET", rendered)
            self.assertNotIn("raw private Telegram message", rendered)


    def test_dashboard_facade_uses_app_state_root_and_desktop_log_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "Application Support" / "T-Sense"
            code_root = root / "bundle-code"
            db_path = state_root / ".tgcs" / "tgcs.db"
            log_path = root / "Logs" / "desktop-backend.log"
            telegram_dir = state_root / ".tgcs" / "telegram"
            demo_report = state_root / "output" / "demo-report.html"
            demo_report.parent.mkdir(parents=True)
            demo_report.write_text("<!doctype html>", encoding="utf-8")

            with (
                patch.object(dashboard_server, "PROJECT_ROOT", state_root),
                patch.object(dashboard_server, "CODE_ROOT", code_root),
                patch.object(dashboard_server, "TELEGRAM_CONFIG_DIR", telegram_dir),
                patch.object(
                    dashboard_server,
                    "telegram_status",
                    return_value={"credentials_ready": True, "session_ready": True},
                ),
                patch.object(
                    dashboard_server,
                    "desk_sources",
                    return_value={"schema_version": "desk_sources_v1", "source_count": 1, "enabled_count": 1},
                ),
                patch.object(
                    dashboard_server,
                    "dashboard_state_payload",
                    return_value={"profiles": [{"profile_id": "jobs-fast"}], "runs": [{"run_id": "run-1"}]},
                ),
                patch.dict("os.environ", {"TSENSE_DESKTOP_LOG": str(log_path)}),
            ):
                status = dashboard_server.desk_support_status(host="127.0.0.1", port=8766, db_path=db_path)

        self.assertEqual(status["app_data_root"], str(state_root))
        self.assertEqual(status["code_root"], str(code_root))
        self.assertEqual(status["database_path"], str(db_path))
        self.assertEqual(status["desktop_log_path"], str(log_path))
        self.assertEqual(status["dashboard_url"], "http://127.0.0.1:8766")
        self.assertEqual(status["source_registry_path"], str(state_root / ".tgcs" / "sources.json"))
        self.assertEqual(status["readiness"]["schema_version"], "desk_support_readiness_v1")
        self.assertEqual(status["readiness"]["status"], "ready")
        self.assertEqual(status["readiness"]["ready_count"], 5)


    def test_real_scan_readiness_marks_user_owned_gates(self):
        readiness = desk_support.real_scan_readiness(
            telegram_status={"credentials_ready": False, "session_ready": False},
            sources_result={"source_count": 0, "enabled_count": 0},
            dashboard_state={"profiles": [], "runs": []},
            demo_report_exists=True,
        )

        self.assertEqual(readiness["schema_version"], "desk_support_readiness_v1")
        self.assertEqual(readiness["status"], "needs_user")
        self.assertEqual(readiness["ready_count"], 1)
        items = {item["label"]: item for item in readiness["items"]}
        self.assertEqual(items["Demo report"]["status"], "ready")
        self.assertEqual(items["Telegram login"]["status"], "needs_user")
        self.assertIn("Finish Telegram setup", items["Telegram login"]["next_action"])


    def test_support_status_reports_legacy_project_data_without_migrating(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "Application Support" / "T-Sense"
            code_root = root / "project-code"
            legacy_tgcs = code_root / ".tgcs"
            legacy_output = code_root / "output"
            legacy_tgcs.mkdir(parents=True)
            legacy_output.mkdir(parents=True)
            (legacy_tgcs / "sources.json").write_text('{"sources":[]}', encoding="utf-8")
            (legacy_output / "demo-report.html").write_text("<html></html>", encoding="utf-8")

            status = desk_support.desk_support_status(
                project_root=state_root,
                code_root=code_root,
                db_path=state_root / ".tgcs" / "tgcs.db",
                telegram_config_dir=state_root / ".tgcs" / "telegram",
                dashboard_url="http://127.0.0.1:8766",
                desktop_log_path=root / "Logs" / "desktop-backend.log",
                legacy_telegram_config_dir=root / ".config" / "tgcli",
                now_fn=lambda: "2026-05-16T14:00:00Z",
            )

        migration = status["migration"]
        labels = [item["label"] for item in migration["legacy_locations"]]
        self.assertEqual(migration["schema_version"], "desk_support_migration_v1")
        self.assertEqual(migration["status"], "manual_required")
        self.assertIn("user-selected", migration["next_action"])
        self.assertIn("Legacy project state", labels)
        self.assertIn("Legacy reports", labels)
        self.assertFalse((state_root / ".tgcs" / "sources.json").exists())


    def test_reveal_support_target_uses_allowlisted_path_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "Application Support" / "T-Sense"
            log_path = root / "Logs" / "desktop-backend.log"
            opened: list[Path] = []

            result = desk_support.reveal_support_target(
                "desktop_log",
                project_root=state_root,
                db_path=state_root / ".tgcs" / "tgcs.db",
                telegram_config_dir=state_root / ".tgcs" / "telegram",
                source_registry_path=state_root / ".tgcs" / "sources.json",
                desktop_log_path=log_path,
                opener=lambda path: opened.append(path),
            )

        self.assertEqual(result["schema_version"], "desk_support_reveal_result_v1")
        self.assertEqual(result["target"], "desktop_log")
        self.assertEqual(result["path"], str(log_path))
        self.assertEqual(opened, [log_path])

        with self.assertRaises(ValueError):
            desk_support.reveal_support_target(
                "../../private",
                project_root=state_root,
                db_path=state_root / ".tgcs" / "tgcs.db",
                telegram_config_dir=state_root / ".tgcs" / "telegram",
                source_registry_path=state_root / ".tgcs" / "sources.json",
                desktop_log_path=log_path,
                opener=lambda path: opened.append(path),
            )


if __name__ == "__main__":
    unittest.main()
