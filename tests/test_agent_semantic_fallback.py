import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def load_report_module(testcase):
    try:
        from scripts import report
    except ImportError as exc:
        testcase.fail(f"scripts.report should exist: {exc}")
    return report


def sample_scan_row() -> dict:
    return {
        "id": 101,
        "message_ref": {"channel": "cointelegraph", "id": 101},
        "channel": "cointelegraph",
        "date": "2026-05-08T09:00:00+00:00",
        "text": "Coinbase launches a new market product.",
    }


class AgentSemanticFallbackTests(unittest.TestCase):
    def test_report_agent_extractor_writes_request_without_calling_llm(self):
        report = load_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "scan.jsonl"
            profile_path = root / "profile.md"
            request_path = root / "extract-request.json"
            output_path = root / "report.md"
            input_path.write_text(json.dumps(sample_scan_row()) + "\n", encoding="utf-8")
            profile_path.write_text("# Market Monitor\n", encoding="utf-8")
            stdout = io.StringIO()

            with patch.dict("os.environ", {}, clear=True):
                with patch.object(report, "extract_jobs") as extract_jobs:
                    with patch("sys.stdout", stdout):
                        exit_code = report.main(
                            [
                                "--input",
                                str(input_path),
                                "--profile",
                                str(profile_path),
                                "--output",
                                str(output_path),
                                "--extractor",
                                "agent",
                                "--write-extraction-request",
                                str(request_path),
                                "--format",
                                "json",
                            ]
                        )
            payload = json.loads(stdout.getvalue())
            request = json.loads(request_path.read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["status"], "agent_extraction_required")
        self.assertEqual(payload["data"]["request_path"], str(request_path))
        self.assertFalse(output_path.exists())
        self.assertEqual(request["schema_version"], "agent_extraction_request_v1")
        self.assertEqual(request["extraction_contract"]["items_schema_version"], "semantic_items_v1")
        self.assertEqual(request["selected_messages"][0]["id"], 101)
        extract_jobs.assert_not_called()

    def test_report_auto_without_key_uses_agent_request(self):
        report = load_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "scan.jsonl"
            profile_path = root / "profile.md"
            output_path = root / "report.md"
            input_path.write_text(json.dumps(sample_scan_row()) + "\n", encoding="utf-8")
            profile_path.write_text("# Market Monitor\n", encoding="utf-8")
            stdout = io.StringIO()

            with patch.dict("os.environ", {}, clear=True):
                with patch.object(report, "extract_jobs") as extract_jobs:
                    with patch("sys.stdout", stdout):
                        exit_code = report.main(
                            [
                                "--input",
                                str(input_path),
                                "--profile",
                                str(profile_path),
                                "--output",
                                str(output_path),
                                "--format",
                                "json",
                            ]
                        )
            payload = json.loads(stdout.getvalue())
            request_path = Path(payload["data"]["request_path"])
            request_exists = request_path.exists()

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["status"], "agent_extraction_required")
        self.assertTrue(request_exists)
        extract_jobs.assert_not_called()

    def test_report_items_json_renders_without_llm_key(self):
        report = load_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "scan.jsonl"
            profile_path = root / "profile.md"
            items_path = root / "items.json"
            output_path = root / "report.md"
            input_path.write_text(json.dumps(sample_scan_row()) + "\n", encoding="utf-8")
            profile_path.write_text("# Market Monitor\n", encoding="utf-8")
            items_path.write_text(
                json.dumps(
                    {
                        "schema_version": "semantic_items_v1",
                        "items": [
                            {
                                "source_message_refs": [{"channel": "cointelegraph", "id": 101}],
                                "company": "Coinbase",
                                "role": "Market signal",
                                "rating": "medium",
                                "why": "Relevant exchange product update.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {}, clear=True):
                with patch.object(report, "extract_jobs") as extract_jobs:
                    exit_code = report.main(
                        [
                            "--input",
                            str(input_path),
                            "--profile",
                            str(profile_path),
                            "--items-json",
                            str(items_path),
                            "--output",
                            str(output_path),
                        ]
                    )
            text = output_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn("Coinbase", text)
        extract_jobs.assert_not_called()

    def test_report_items_json_rejects_unknown_source_refs(self):
        report = load_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "scan.jsonl"
            profile_path = root / "profile.md"
            items_path = root / "items.json"
            input_path.write_text(json.dumps(sample_scan_row()) + "\n", encoding="utf-8")
            profile_path.write_text("# Market Monitor\n", encoding="utf-8")
            items_path.write_text(
                json.dumps(
                    {
                        "schema_version": "semantic_items_v1",
                        "items": [
                            {
                                "source_message_refs": [{"channel": "wrong", "id": 999}],
                                "company": "Coinbase",
                                "role": "Market signal",
                                "rating": "medium",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with patch("sys.stdout", stdout):
                exit_code = report.main(
                    [
                        "--input",
                        str(input_path),
                        "--profile",
                        str(profile_path),
                        "--items-json",
                        str(items_path),
                        "--format",
                        "json",
                    ]
                )
            payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 3)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "items_json_invalid")

    def test_report_items_json_rejects_private_semantic_item_fields(self):
        report = load_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "scan.jsonl"
            profile_path = root / "profile.md"
            items_path = root / "items.json"
            input_path.write_text(json.dumps(sample_scan_row()) + "\n", encoding="utf-8")
            profile_path.write_text("# Market Monitor\n", encoding="utf-8")
            items_path.write_text(
                json.dumps(
                    {
                        "schema_version": "semantic_items_v1",
                        "items": [
                            {
                                "source_message_refs": [{"channel": "cointelegraph", "id": 101}],
                                "company": "Coinbase",
                                "role": "Market signal",
                                "rating": "medium",
                                "raw_text": "Coinbase launches a new market product.",
                                "debug": {"argv": ["tgcs", "report"], "token": "123456:ABCDEF_secret"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with patch("sys.stdout", stdout):
                exit_code = report.main(
                    [
                        "--input",
                        str(input_path),
                        "--profile",
                        str(profile_path),
                        "--items-json",
                        str(items_path),
                        "--format",
                        "json",
                    ]
                )
            payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 3)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "items_json_invalid")
        self.assertIn("raw_text", payload["error"]["message"])
        self.assertNotIn("Coinbase launches a new market product", json.dumps(payload, ensure_ascii=False))

    def test_daily_report_propagates_agent_extraction_request(self):
        from scripts import agent_cli, daily_report

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "sources.json"
            profile_path = root / "profile.md"
            output_dir = root / "output"
            request_path = output_dir / "extract-request.json"
            registry_path.write_text(
                json.dumps({"schema_version": "source_registry_v1", "sources": []}),
                encoding="utf-8",
            )
            profile_path.write_text("# Profile\n", encoding="utf-8")
            calls = []
            stdout = io.StringIO()

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                if "scan.py" in str(cmd[1]):
                    scan_path = Path(cmd[cmd.index("--output") + 1])
                    scan_path.write_text(json.dumps(sample_scan_row()) + "\n", encoding="utf-8")
                    return SimpleNamespace(
                        returncode=0,
                        stdout=json.dumps(
                            agent_cli.envelope_success(
                                {"output_path": str(scan_path), "source_health": []}
                            )
                        ),
                    )
                return SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps(
                        agent_cli.envelope_success(
                            {
                                "status": "agent_extraction_required",
                                "request_path": str(request_path),
                                "items_output_path": str(output_dir / "extracted-items.json"),
                            }
                        )
                    ),
                )

            with patch.object(daily_report.subprocess, "run", side_effect=fake_run):
                with patch("sys.stdout", stdout):
                    exit_code = daily_report.main(
                        [
                            "--source-registry",
                            str(registry_path),
                            "--profile",
                            str(profile_path),
                            "--output-dir",
                            str(output_dir),
                            "--extractor",
                            "agent",
                            "--format",
                            "json",
                        ]
                    )
            payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["status"], "agent_extraction_required")
        self.assertEqual(payload["data"]["extraction_request_path"], str(request_path))
        self.assertIn("--extractor", calls[1])


if __name__ == "__main__":
    unittest.main()
