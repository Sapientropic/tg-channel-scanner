import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .helpers import load_report_module, sample_extracted_jobs, sample_messages


class ReportCliTests(unittest.TestCase):
    def test_dry_run_prompt_redacts_contacts_and_does_not_call_llm(self):
        report = load_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "scan_20260506_080000.jsonl"
            profile_path = root / "profile.md"
            prompt_path = root / "prompt.md"
            input_path.write_text(
                json.dumps(sample_messages()[0], ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            profile_path.write_text(
                "Contact me at candidate@example.com for React roles.",
                encoding="utf-8",
            )

            with patch.object(report, "extract_jobs") as extract_jobs:
                exit_code = report.main(
                    [
                        "--input",
                        str(input_path),
                        "--profile",
                        str(profile_path),
                        "--dry-run-prompt",
                        str(prompt_path),
                        "--redact-contact-info",
                    ]
                )
            text = prompt_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        extract_jobs.assert_not_called()
        self.assertIn("[redacted-email]", text)
        self.assertNotIn("candidate@example.com", text)
        self.assertNotIn("hr@codesrc.ru", text)


    def test_invalid_llm_json_writes_debug_response_and_exits_nonzero(self):
        report = load_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "scan_20260506_080000.jsonl"
            profile_path = root / "profile.md"
            output_path = root / "job-scan-report.md"
            input_path.write_text(
                json.dumps(sample_messages()[0], ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            profile_path.write_text("Senior Frontend Developer", encoding="utf-8")
            stderr = io.StringIO()

            with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True):
                with patch.object(
                    report,
                    "extract_jobs_with_metadata",
                    side_effect=report.ReportError("LLM response was not valid JSON", "bad"),
                ):
                    with patch("sys.stderr", stderr):
                        exit_code = report.main(
                            [
                                "--input",
                                str(input_path),
                                "--profile",
                                str(profile_path),
                                "--output",
                                str(output_path),
                            ]
                        )
            debug_path = output_path.with_suffix(".llm-response.txt")
            debug_exists = debug_path.exists()
            debug_text = debug_path.read_text(encoding="utf-8") if debug_exists else ""

        self.assertEqual(exit_code, 1)
        self.assertIn("not valid JSON", stderr.getvalue())
        self.assertTrue(debug_exists)
        self.assertEqual(debug_text, "bad")


    def test_invalid_llm_json_json_mode_surfaces_repairable_diagnostic(self):
        report = load_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "scan_20260506_080000.jsonl"
            profile_path = root / "profile.md"
            output_path = root / "job-scan-report.md"
            input_path.write_text(
                json.dumps(sample_messages()[0], ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            profile_path.write_text("Senior Frontend Developer", encoding="utf-8")
            stdout = io.StringIO()

            diagnostic = {
                "code": "llm_output_truncated",
                "severity": "failure",
                "message": "The LLM response ended before a complete JSON object could be parsed.",
                "next_step": "Raise semantic_max_tokens, lower semantic_max_messages, or narrow the prefilter.",
            }
            with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True):
                with patch.object(
                    report,
                    "extract_jobs_with_metadata",
                    side_effect=report.ReportError(
                        "LLM response was not valid JSON",
                        '{"items": [',
                        code="llm_output_truncated",
                        next_step=diagnostic["next_step"],
                        details={"diagnostics": [diagnostic], "llm": {"provider": "deepseek", "max_tokens": 2000}},
                    ),
                ):
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

        self.assertEqual(exit_code, 1)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "llm_output_truncated")
        self.assertEqual(payload["error"]["details"]["diagnostics"][0]["code"], "llm_output_truncated")
        self.assertIn("semantic_max_tokens", payload["error"]["next_step"])


    def test_html_output_writes_markdown_and_html_from_one_extraction(self):
        report = load_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "scan_20260506_080000.jsonl"
            profile_path = root / "profile.md"
            output_path = root / "job-scan-report.md"
            html_output_path = root / "job-scan-report.html"
            input_path.write_text(
                json.dumps(sample_messages()[0], ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            profile_path.write_text("Senior Frontend Developer", encoding="utf-8")

            extraction = report.ExtractionResult(items=sample_extracted_jobs()[:1], llm={"provider": "openai"})
            with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=True):
                with patch.object(report, "extract_jobs_with_metadata", return_value=extraction) as extract_jobs:
                    exit_code = report.main(
                        [
                            "--input",
                            str(input_path),
                            "--profile",
                            str(profile_path),
                            "--output",
                            str(output_path),
                            "--html-output",
                            str(html_output_path),
                        ]
                    )

            markdown = output_path.read_text(encoding="utf-8")
            html = html_output_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        extract_jobs.assert_called_once()
        self.assertIn("# Job Scan Report", markdown)
        self.assertIn("<!doctype html>", html.lower())


    def test_json_output_includes_llm_metadata_from_extraction_result(self):
        report = load_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "scan_20260506_080000.jsonl"
            profile_path = root / "profile.md"
            input_path.write_text(
                json.dumps(sample_messages()[0], ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            profile_path.write_text("Senior Frontend Developer", encoding="utf-8")
            stdout = io.StringIO()

            def fake_extract_jobs(**kwargs):
                return report.ExtractionResult(
                    items=sample_extracted_jobs()[:1],
                    llm={
                        "provider": "deepseek",
                        "model": "deepseek-v4-flash",
                        "usage": {
                            "prompt_cache_hit_tokens": 80,
                            "prompt_cache_miss_tokens": 20,
                        },
                    },
                )

            with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "sk-test"}, clear=True):
                with patch("sys.stdout", stdout):
                    exit_code = report.main(
                        [
                            "--input",
                            str(input_path),
                            "--profile",
                            str(profile_path),
                            "--format",
                            "json",
                        ],
                        extract_jobs_override=fake_extract_jobs,
                    )
            payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["data"]["llm"]["provider"], "deepseek")
        self.assertEqual(payload["data"]["llm"]["usage"]["prompt_cache_hit_tokens"], 80)


    def test_demo_fixture_html_only_runs_without_llm_or_telegram(self):
        report = load_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "demo-report.md"

            with patch.object(report, "extract_jobs") as extract_jobs:
                exit_code = report.main(
                    [
                        "--input",
                        "templates/demo/fixtures/demo-scan.jsonl",
                        "--profile",
                        "templates/demo/fixtures/demo-profile.md",
                        "--html-only",
                        "templates/demo/fixtures/demo-report.md",
                        "--output",
                        str(output_path),
                    ]
                )

            html_path = output_path.with_suffix(".html")
            self.assertEqual(exit_code, 0)
            extract_jobs.assert_not_called()
            self.assertTrue(html_path.exists())



if __name__ == "__main__":
    unittest.main()
