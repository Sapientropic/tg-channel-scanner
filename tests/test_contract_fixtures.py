import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import agent_cli, monitor, report


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "contracts"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def semantic_messages() -> list[dict]:
    return [
        {
            "id": 42,
            "message_ref": {"channel": "jobs", "id": 42},
            "channel": "jobs",
            "date": "2026-05-13T00:00:00Z",
            "text": "We are hiring a Senior TypeScript Engineer.",
        }
    ]


def normalize_monitor_result(data: dict) -> dict:
    return {
        "schema_version": data.get("schema_version"),
        "status": data.get("status"),
        "run_id": data.get("run_id"),
        "manifest_path": data.get("manifest_path"),
        "db_path": data.get("db_path"),
        "report_path": data.get("report_path"),
        "html_path": data.get("html_path"),
        "review_card_count": data.get("review_card_count"),
        "alert_count": data.get("alert_count"),
        "prefilter": data.get("prefilter"),
        "semantic": data.get("semantic"),
        "diagnostics": data.get("diagnostics"),
        "llm": data.get("llm"),
        "delivery_attempts": data.get("delivery_attempts"),
        "extraction_request_path": data.get("extraction_request_path"),
        "items_output_path": data.get("items_output_path"),
    }


def normalize_manifest(manifest: dict) -> dict:
    return {
        "schema_version": manifest.get("schema_version"),
        "run_id": manifest.get("run_id"),
        "profile_id": manifest.get("profile_id"),
        "profile_path": manifest.get("profile_path"),
        "source_registry_path": manifest.get("source_registry_path"),
        "scan_window": manifest.get("scan_window"),
        "scan": manifest.get("scan"),
        "source_filters": manifest.get("source_filters"),
        "alert_rule": manifest.get("alert_rule"),
        "semantic": manifest.get("semantic"),
        "alert_schedule": manifest.get("alert_schedule"),
        "prefilter": manifest.get("prefilter"),
        "status": manifest.get("status"),
        "artifact_summaries": [
            {key: artifact.get(key) for key in (
                "artifact_id",
                "type",
                "path",
                "run_id",
                "category",
                "format",
                "display_name",
                "display_path",
            )}
            for artifact in manifest.get("artifacts", [])
        ],
        "report_status": manifest.get("report_status"),
        "alert_count": manifest.get("alert_count"),
        "review_card_count": manifest.get("review_card_count"),
        "diagnostics": manifest.get("diagnostics"),
        "error_summary": manifest.get("error_summary"),
        "llm": manifest.get("llm"),
        "delivery_attempts": manifest.get("delivery_attempts"),
    }


class ContractFixtureTests(unittest.TestCase):
    def test_agent_envelope_helpers_match_contract_fixtures(self):
        success = agent_cli.envelope_success({"status": "complete", "count": 1}, {"command": "doctor"})
        error = agent_cli.envelope_error(
            code="registry_invalid",
            message="Source registry is invalid.",
            retryable=False,
            next_step="Run source_registry.py validate and fix the registry.",
            details={"path": ".tgcs/sources.json"},
            meta={"command": "source_registry"},
        )

        self.assertEqual(success, load_fixture("agent_envelope_v1.success.json"))
        self.assertEqual(error, load_fixture("agent_envelope_v1.error.json"))

    def test_semantic_items_fixture_is_valid_contract_input(self):
        fixture = load_fixture("semantic_items_v1.valid.json")

        items = report.load_semantic_items(
            str(FIXTURE_DIR / "semantic_items_v1.valid.json"),
            semantic_messages(),
        )

        self.assertEqual(items, fixture["items"])

    def test_semantic_items_private_fixture_is_rejected_without_echoing_values(self):
        fixture = load_fixture("semantic_items_v1.private-field.json")

        with self.assertRaises(report.ReportError) as raised:
            report.load_semantic_items(
                str(FIXTURE_DIR / "semantic_items_v1.private-field.json"),
                semantic_messages(),
            )

        message = str(raised.exception)
        self.assertIn("raw_text", message)
        for denied in fixture["denied_strings"]:
            with self.subTest(denied=denied):
                self.assertNotIn(denied, message)

    def test_monitor_run_and_manifest_match_minimal_contract_fixtures(self):
        raw_text = "RAW_MONITOR_SCAN_TEXT_SHOULD_NOT_SURFACE"
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
            (root / ".tgcs" / "profiles.toml").write_text(
                "\n".join(
                    [
                        'schema_version = "profile_run_config_v1"',
                        "",
                        "[[profiles]]",
                        'id = "market-news"',
                        'path = "profiles/templates/market-news.md"',
                        "enabled = true",
                        'source_registry = ".tgcs/sources.json"',
                        'source_topics = ["market-news"]',
                        'alert_rule = "high_new_or_changed"',
                        'alert_schedule_mode = "all_day"',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            scan = root / "scan.jsonl"
            scan.write_text(
                json.dumps(
                    {
                        "id": 42,
                        "channel": "jobs",
                        "date": "2026-05-13T00:00:00Z",
                        "text": raw_text,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            output_dir = root / "output"
            db_path = root / ".tgcs" / "tgcs.db"
            report_path = output_dir / "runs" / "run-contract" / "report.md"
            html_path = output_dir / "runs" / "run-contract" / "report.html"

            def fake_run_json_command(cmd):
                self.assertIn("report.py", str(cmd[1]))
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
                            "scan_path": str(scan),
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
                                    "topic": "Developer opportunity",
                                    "company": "ACME Labs",
                                    "role": "Senior TypeScript Engineer",
                                    "rating": "high",
                                    "why": "Strong TypeScript and React match.",
                                    "decision_state": {"schema_version": "decision_state_v1", "status": "new"},
                                    "source_message_refs": [{"channel": "jobs", "id": 42}],
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
                                "run-contract",
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
            manifest = json.loads(
                (output_dir / "runs" / "run-contract" / "run-manifest.json").read_text(encoding="utf-8")
            )

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(
            normalize_monitor_result(payload["data"]),
            load_fixture("monitor_run_result_v1.minimal.json"),
        )
        self.assertEqual(
            normalize_manifest(manifest),
            load_fixture("run_manifest_v1.minimal.json"),
        )
        surfaces = json.dumps(
            {
                "monitor_result": normalize_monitor_result(payload["data"]),
                "manifest": normalize_manifest(manifest),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        self.assertNotIn(raw_text, surfaces)


if __name__ == "__main__":
    unittest.main()
