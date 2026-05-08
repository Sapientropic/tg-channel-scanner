import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import monitor


class MonitorTests(unittest.TestCase):
    def test_monitor_run_with_scan_input_writes_manifest_and_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "profiles" / "templates").mkdir(parents=True)
            (root / "profiles" / "templates" / "market-news.md").write_text(
                "# Profile\n\n## Search Rules\n1. Keep market items.\n",
                encoding="utf-8",
            )
            (root / ".tgcs").mkdir()
            (root / ".tgcs" / "sources.json").write_text(
                json.dumps({"schema_version": "source_registry_v1", "sources": []}),
                encoding="utf-8",
            )
            scan = root / "scan.jsonl"
            scan.write_text("{}", encoding="utf-8")
            output_dir = root / "output"
            db_path = root / ".tgcs" / "tgcs.db"
            report_path = output_dir / "runs" / "run-test" / "report.md"
            html_path = output_dir / "runs" / "run-test" / "report.html"

            def fake_run_json_command(cmd):
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
                            "items": [
                                {
                                    "topic": "Exchange outage",
                                    "rating": "high",
                                    "why": "Decision relevant.",
                                    "text": "raw message body",
                                    "decision_state": {
                                        "status": "new",
                                        "semantic_cluster": "cluster-1",
                                    },
                                    "source_message_refs": [{"channel": "cointelegraph", "id": 123}],
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
                                "run-test",
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
            manifest = json.loads((output_dir / "runs" / "run-test" / "run-manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["review_card_count"], 1)
        self.assertEqual(payload["data"]["alert_count"], 1)
        self.assertEqual(manifest["schema_version"], "run_manifest_v1")
        self.assertEqual(manifest["review_card_count"], 1)


if __name__ == "__main__":
    unittest.main()
