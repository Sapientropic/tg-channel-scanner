import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import monitor


class MonitorPrefilterManifestTests(unittest.TestCase):
    def test_prefilter_skips_semantic_stage_without_keyword_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "profiles" / "templates").mkdir(parents=True)
            (root / "profiles" / "templates" / "jobs.md").write_text(
                "# Profile\n\n## Search Rules\n1. Keep jobs.\n",
                encoding="utf-8",
            )
            (root / ".tgcs").mkdir()
            (root / ".tgcs" / "sources.json").write_text(
                json.dumps(
                    {
                        "schema_version": "source_registry_v1",
                        "sources": [
                            {
                                "source_id": "telegram:jobs",
                                "username": "jobs",
                                "channel_id": None,
                                "label": "Jobs",
                                "topics": ["jobs"],
                                "priority": "normal",
                                "expected_language": "",
                                "scan_window_hours": 24,
                                "enabled": True,
                                "notes": "",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "output"
            db_path = root / ".tgcs" / "tgcs.db"
            calls: list[list[str | Path]] = []

            def fake_run_json_command(cmd):
                calls.append(cmd)
                self.assertIn("scan.py", str(cmd[1]))
                output_path = Path(cmd[cmd.index("--output") + 1])
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(
                    json.dumps(
                        {
                            "id": 1,
                            "channel": "jobs",
                            "date": "2026-05-08T08:30:00Z",
                            "text": "Unrelated community chat with no role signal.",
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                output_path.with_suffix(".meta.json").write_text(
                    json.dumps({"scan_window": "Last 2 hours", "source_health": []}),
                    encoding="utf-8",
                )
                return (
                    0,
                    {
                        "ok": True,
                        "data": {
                            "output_path": str(output_path),
                            "meta_path": str(output_path.with_suffix(".meta.json")),
                            "message_count": 1,
                            "source_health": [],
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
                                "jobs-fast",
                                "--run-id",
                                "run-prefilter",
                                "--output-dir",
                                str(output_dir),
                                "--db",
                                str(db_path),
                                "--format",
                                "json",
                            ]
                        )

            payload = json.loads(stdout.getvalue())
            manifest = json.loads(
                (output_dir / "runs" / "run-prefilter" / "run-manifest.json").read_text(encoding="utf-8")
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(payload["data"]["status"], "prefilter_no_match")
        self.assertEqual(payload["data"]["review_card_count"], 0)
        self.assertEqual(manifest["prefilter"]["matched_count"], 0)

    def test_scan_failure_manifest_keeps_scan_diagnostics_and_sidecars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "profiles" / "templates").mkdir(parents=True)
            (root / "profiles" / "templates" / "jobs.md").write_text("# Jobs", encoding="utf-8")
            registry = root / ".tgcs" / "sources.json"
            registry.parent.mkdir(parents=True)
            registry.write_text(
                json.dumps(
                    {
                        "schema_version": "source_registry_v1",
                        "sources": [{"source_id": "telegram:missing", "username": "missing", "topics": ["jobs"]}],
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "output"
            db_path = root / ".tgcs" / "tgcs.db"

            def fake_run_json_command(cmd):
                run_dir = output_dir / "runs" / "run-scan-failed"
                run_dir.mkdir(parents=True, exist_ok=True)
                (run_dir / "scan.meta.json").write_text(
                    json.dumps(
                        {
                            "total_messages_collected": 0,
                            "failed_channels": ["missing"],
                            "failure_count": 1,
                            "source_health": [
                                {
                                    "channel": "missing",
                                    "failure": "ScanError",
                                    "last_error": "Cannot resolve channel: missing",
                                }
                            ],
                        }
                    ),
                    encoding="utf-8",
                )
                (run_dir / "scan.errors.log").write_text("[missing] Cannot resolve channel", encoding="utf-8")
                return 1, {"ok": False, "error": {"code": "scan_failed"}}, "scan failed"

            stdout = io.StringIO()
            with patch.object(monitor, "PROJECT_ROOT", root):
                with patch.object(monitor, "run_json_command", side_effect=fake_run_json_command):
                    with patch("sys.stdout", stdout):
                        exit_code = monitor.main(
                            [
                                "run",
                                "--profile-id",
                                "jobs-fast",
                                "--run-id",
                                "run-scan-failed",
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
                (output_dir / "runs" / "run-scan-failed" / "run-manifest.json").read_text(encoding="utf-8")
            )

        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(manifest["diagnostics"][0]["code"], "channel_failures")
        self.assertIn("no_messages_fetched", {item["code"] for item in manifest["diagnostics"]})
        self.assertIn("scan_meta", {item["type"] for item in manifest["artifacts"]})
        self.assertIn("scan_errors", {item["type"] for item in manifest["artifacts"]})

    def test_prefilter_runs_report_on_keyword_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "profiles" / "templates").mkdir(parents=True)
            (root / "profiles" / "templates" / "jobs.md").write_text(
                "# Profile\n\n## Search Rules\n1. Keep jobs.\n",
                encoding="utf-8",
            )
            (root / ".tgcs").mkdir()
            (root / ".tgcs" / "sources.json").write_text(
                json.dumps(
                    {
                        "schema_version": "source_registry_v1",
                        "sources": [
                            {
                                "source_id": "telegram:jobs",
                                "username": "jobs",
                                "topics": ["jobs"],
                                "scan_window_hours": 24,
                                "enabled": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "output"
            db_path = root / ".tgcs" / "tgcs.db"
            calls: list[list[str | Path]] = []

            def fake_run_json_command(cmd):
                calls.append(cmd)
                script = str(cmd[1])
                if "scan.py" in script:
                    output_path = Path(cmd[cmd.index("--output") + 1])
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(
                        json.dumps(
                            {
                                "id": 1,
                                "channel": "jobs",
                                "date": "2026-05-08T08:30:00Z",
                                "text": "We are hiring a TypeScript engineer.",
                            }
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                    output_path.with_suffix(".meta.json").write_text(
                        json.dumps({"total_messages_collected": 1, "source_health": []}),
                        encoding="utf-8",
                    )
                    return (
                        0,
                        {
                            "ok": True,
                            "data": {
                                "output_path": str(output_path),
                                "message_count": 1,
                                "source_health": [],
                            },
                        },
                        "",
                    )
                self.assertIn("report.py", script)
                scan_input = Path(cmd[cmd.index("--input") + 1])
                self.assertEqual(scan_input.name, "prefiltered-scan.jsonl")
                self.assertEqual(cmd[cmd.index("--max-messages") + 1], "40")
                self.assertEqual(cmd[cmd.index("--max-tokens") + 1], "6000")
                self.assertEqual(cmd[cmd.index("--semantic-batch-size") + 1], "20")
                self.assertEqual(cmd[cmd.index("--semantic-concurrency") + 1], "2")
                report_path = output_dir / "runs" / "run-prefilter-hit" / "report.md"
                html_path = output_dir / "runs" / "run-prefilter-hit" / "report.html"
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
                            "scan_path": str(scan_input),
                            "items": [
                                {
                                    "topic": "TypeScript engineer",
                                    "rating": "high",
                                    "decision_state": {"status": "new"},
                                    "source_message_refs": [{"channel": "jobs", "id": 1}],
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
                                "jobs-fast",
                                "--run-id",
                                "run-prefilter-hit",
                                "--output-dir",
                                str(output_dir),
                                "--db",
                                str(db_path),
                                "--format",
                                "json",
                            ]
                        )

            payload = json.loads(stdout.getvalue())
            manifest = json.loads(
                (output_dir / "runs" / "run-prefilter-hit" / "run-manifest.json").read_text(encoding="utf-8")
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(calls), 2)
        self.assertEqual(payload["data"]["review_card_count"], 1)
        self.assertEqual(manifest["prefilter"]["matched_count"], 1)
        self.assertEqual(manifest["prefilter"]["semantic_stage"], "report_ran")
        self.assertEqual(len(manifest["commands"]), 2)

    def test_profile_concurrency_settings_flow_to_scan_report_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "profiles" / "templates").mkdir(parents=True)
            (root / "profiles" / "templates" / "jobs.md").write_text(
                "# Profile\n\n## Search Rules\n1. Keep jobs.\n",
                encoding="utf-8",
            )
            (root / ".tgcs").mkdir()
            config_path = root / ".tgcs" / "profiles.toml"
            config_path.write_text(
                "\n".join(
                    [
                        'schema_version = "profile_run_config_v1"',
                        "",
                        "[[profiles]]",
                        'id = "jobs-fast"',
                        'path = "profiles/templates/jobs.md"',
                        'source_registry = ".tgcs/sources.json"',
                        'source_topics = ["jobs"]',
                        "prefilter_enabled = true",
                        'prefilter_keywords = ["hiring"]',
                        "semantic_max_messages = 60",
                        "semantic_max_tokens = 6000",
                        "scan_concurrency = 3",
                        "semantic_batch_size = 20",
                        "semantic_concurrency = 2",
                    ]
                ),
                encoding="utf-8",
            )
            (root / ".tgcs" / "sources.json").write_text(
                json.dumps(
                    {
                        "schema_version": "source_registry_v1",
                        "sources": [
                            {
                                "source_id": "telegram:jobs",
                                "username": "jobs",
                                "topics": ["jobs"],
                                "scan_window_hours": 24,
                                "enabled": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "output"
            db_path = root / ".tgcs" / "tgcs.db"

            def fake_run_json_command(cmd):
                script = str(cmd[1])
                if "scan.py" in script:
                    self.assertEqual(cmd[cmd.index("--scan-concurrency") + 1], "3")
                    self.assertEqual(cmd[cmd.index("--delay") + 1], "0.2")
                    output_path = Path(cmd[cmd.index("--output") + 1])
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(
                        json.dumps(
                            {
                                "id": 1,
                                "channel": "jobs",
                                "date": "2026-05-08T08:30:00Z",
                                "text": "We are hiring a TypeScript engineer.",
                            }
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                    output_path.with_suffix(".meta.json").write_text(
                        json.dumps({"total_messages_collected": 1, "source_health": []}),
                        encoding="utf-8",
                    )
                    return (
                        0,
                        {
                            "ok": True,
                            "data": {
                                "output_path": str(output_path),
                                "message_count": 1,
                                "source_health": [],
                            },
                        },
                        "",
                    )
                self.assertIn("report.py", script)
                self.assertEqual(cmd[cmd.index("--semantic-batch-size") + 1], "20")
                self.assertEqual(cmd[cmd.index("--semantic-concurrency") + 1], "2")
                report_path = output_dir / "runs" / "run-concurrency" / "report.md"
                html_path = output_dir / "runs" / "run-concurrency" / "report.html"
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
                                    "topic": "TypeScript engineer",
                                    "rating": "high",
                                    "decision_state": {"status": "new"},
                                    "source_message_refs": [{"channel": "jobs", "id": 1}],
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
                                "jobs-fast",
                                "--run-id",
                                "run-concurrency",
                                "--config",
                                str(config_path),
                                "--output-dir",
                                str(output_dir),
                                "--db",
                                str(db_path),
                                "--format",
                                "json",
                            ]
                        )

            payload = json.loads(stdout.getvalue())
            manifest = json.loads(
                (output_dir / "runs" / "run-concurrency" / "run-manifest.json").read_text(encoding="utf-8")
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(manifest["scan"]["concurrency"], 3)
        self.assertEqual(manifest["scan"]["delay_seconds"], 0.2)
        self.assertEqual(manifest["semantic"]["batch_size"], 20)
        self.assertEqual(manifest["semantic"]["concurrency"], 2)
        self.assertEqual(payload["data"]["semantic"]["batch_size"], 20)
        self.assertEqual(payload["data"]["semantic"]["concurrency"], 2)

    def test_prefilter_report_failure_records_llm_truncation_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "profiles" / "templates").mkdir(parents=True)
            (root / "profiles" / "templates" / "jobs.md").write_text(
                "# Profile\n\n## Search Rules\n1. Keep jobs.\n",
                encoding="utf-8",
            )
            (root / ".tgcs").mkdir()
            (root / ".tgcs" / "sources.json").write_text(
                json.dumps(
                    {
                        "schema_version": "source_registry_v1",
                        "sources": [
                            {
                                "source_id": "telegram:jobs",
                                "username": "jobs",
                                "topics": ["jobs"],
                                "scan_window_hours": 24,
                                "enabled": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "output"
            db_path = root / ".tgcs" / "tgcs.db"

            def fake_run_json_command(cmd):
                script = str(cmd[1])
                if "scan.py" in script:
                    output_path = Path(cmd[cmd.index("--output") + 1])
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(
                        json.dumps(
                            {
                                "id": 1,
                                "channel": "jobs",
                                "date": "2026-05-08T08:30:00Z",
                                "text": "We are hiring a TypeScript engineer.",
                            }
                        )
                        + "\n",
                        encoding="utf-8",
                    )
                    output_path.with_suffix(".meta.json").write_text(
                        json.dumps({"total_messages_collected": 1, "source_health": []}),
                        encoding="utf-8",
                    )
                    return (
                        0,
                        {
                            "ok": True,
                            "data": {
                                "output_path": str(output_path),
                                "message_count": 1,
                                "source_health": [],
                            },
                        },
                        "",
                    )
                diagnostic = {
                    "code": "llm_output_truncated",
                    "severity": "failure",
                    "message": "The LLM response ended before complete JSON.",
                    "next_step": "Raise semantic_max_tokens or lower semantic_max_messages.",
                }
                return (
                    1,
                    {
                        "ok": False,
                        "error": {
                            "code": "llm_output_truncated",
                            "message": "LLM response was not valid JSON",
                            "retryable": True,
                            "next_step": diagnostic["next_step"],
                            "details": {
                                "diagnostics": [diagnostic],
                                "llm": {"provider": "deepseek", "max_tokens": 2000},
                            },
                        },
                    },
                    "Raw LLM response saved to report.llm-response.txt",
                )

            stdout = io.StringIO()
            with patch.object(monitor, "PROJECT_ROOT", root):
                with patch.object(monitor, "run_json_command", side_effect=fake_run_json_command):
                    with patch("sys.stdout", stdout):
                        exit_code = monitor.main(
                            [
                                "run",
                                "--profile-id",
                                "jobs-fast",
                                "--run-id",
                                "run-llm-truncated",
                                "--output-dir",
                                str(output_dir),
                                "--db",
                                str(db_path),
                                "--format",
                                "json",
                            ]
                        )

            payload = json.loads(stdout.getvalue())
            manifest = json.loads(
                (output_dir / "runs" / "run-llm-truncated" / "run-manifest.json").read_text(encoding="utf-8")
            )

        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["ok"])
        self.assertIn("semantic_max_tokens", payload["error"]["next_step"])
        self.assertEqual(manifest["prefilter"]["semantic_stage"], "report_failed")
        self.assertEqual(manifest["diagnostics"][0]["code"], "llm_output_truncated")
        self.assertEqual(manifest["llm"]["provider"], "deepseek")

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
        self.assertEqual(payload["data"]["diagnostics"][0]["code"], "scan_incomplete")
        self.assertEqual(manifest["diagnostics"][0]["code"], "scan_incomplete")

    def test_fast_jobs_scan_input_records_prefilter_bypass_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "profiles" / "templates").mkdir(parents=True)
            (root / "profiles" / "templates" / "jobs.md").write_text(
                "# Profile\n\n## Search Rules\n1. Keep jobs.\n",
                encoding="utf-8",
            )
            scan = root / "scan.jsonl"
            scan.write_text(
                json.dumps(
                    {
                        "id": 1,
                        "channel": "jobs",
                        "date": "2026-05-08T08:30:00Z",
                        "text": "We are hiring a TypeScript engineer.",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            output_dir = root / "output"
            db_path = root / ".tgcs" / "tgcs.db"
            report_path = output_dir / "runs" / "run-scan-input" / "report.md"
            html_path = output_dir / "runs" / "run-scan-input" / "report.html"

            def fake_run_json_command(cmd):
                self.assertIn("report.py", str(cmd[1]))
                self.assertEqual(Path(cmd[cmd.index("--input") + 1]), scan)
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
                            "items": [],
                        },
                    },
                    "",
                )

            with patch.object(monitor, "PROJECT_ROOT", root):
                with patch.object(monitor, "run_json_command", side_effect=fake_run_json_command):
                    exit_code = monitor.main(
                        [
                            "run",
                            "--profile-id",
                            "jobs-fast",
                            "--run-id",
                            "run-scan-input",
                            "--scan-input",
                            str(scan),
                            "--output-dir",
                            str(output_dir),
                            "--db",
                            str(db_path),
                            "--format",
                            "json",
                        ]
                    )

            manifest = json.loads(
                (output_dir / "runs" / "run-scan-input" / "run-manifest.json").read_text(encoding="utf-8")
            )

        self.assertEqual(exit_code, 0)
        self.assertFalse(manifest["prefilter"]["enabled"])
        self.assertEqual(manifest["prefilter"]["semantic_stage"], "bypassed_scan_input")
        self.assertEqual(manifest["prefilter"]["bypass_reason"], "scan_input")



if __name__ == "__main__":
    unittest.main()
