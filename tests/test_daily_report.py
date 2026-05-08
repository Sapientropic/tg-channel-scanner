import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def load_daily_report_module(testcase):
    try:
        from scripts import daily_report
    except ImportError as exc:
        testcase.fail(f"scripts.daily_report should exist: {exc}")
    return daily_report


class DailyReportTests(unittest.TestCase):
    def test_default_report_output_path_uses_scan_date(self):
        daily_report = load_daily_report_module(self)

        path = daily_report.default_report_output_path(
            Path("output"), scan_date="2026-05-06"
        )

        self.assertEqual(path, Path("output") / "job-scan-report-2026-05-06.md")

    def test_main_runs_scan_then_report_with_this_run_scan_file(self):
        daily_report = load_daily_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "output"
            output_dir.mkdir()
            report_file = output_dir / "job-scan-report-2026-05-06.md"
            calls = []

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                if "scan.py" in str(cmd[1]):
                    scan_file = Path(cmd[cmd.index("--output") + 1])
                    scan_file.write_text("{}", encoding="utf-8")
                return None

            with patch.object(daily_report.subprocess, "run", side_effect=fake_run):
                exit_code = daily_report.main(
                    [
                        "channel_lists/example.txt",
                        "--profile",
                        "profiles/example.md",
                        "--output-dir",
                        str(output_dir),
                        "--report-output",
                        str(report_file),
                        "--next-scan-note",
                        "Next scan scheduled for tomorrow.",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(calls), 2)
        self.assertIn("scan.py", str(calls[0][1]))
        self.assertIn("report.py", str(calls[1][1]))
        self.assertIn("--output", calls[0])
        self.assertIn(calls[0][calls[0].index("--output") + 1], calls[1])
        self.assertIn(str(report_file), calls[1])
        self.assertIn("Next scan scheduled for tomorrow.", calls[1])

    def test_main_uses_this_run_scan_file_instead_of_latest_mtime(self):
        daily_report = load_daily_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "output"
            output_dir.mkdir()
            stale_scan = output_dir / "scan_20991231_235959.jsonl"
            stale_scan.write_text("stale", encoding="utf-8")
            calls = []

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                if "scan.py" in str(cmd[1]):
                    scan_file = Path(cmd[cmd.index("--output") + 1])
                    scan_file.write_text("fresh", encoding="utf-8")
                return None

            with patch.object(daily_report.subprocess, "run", side_effect=fake_run):
                exit_code = daily_report.main(
                    [
                        "channel_lists/example.txt",
                        "--profile",
                        "profiles/example.md",
                        "--output-dir",
                        str(output_dir),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertIn(calls[0][calls[0].index("--output") + 1], calls[1])
        self.assertNotIn(str(stale_scan), calls[1])

    def test_main_fails_when_this_run_scan_file_is_missing(self):
        daily_report = load_daily_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "output"
            output_dir.mkdir()
            calls = []

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                return None

            with patch.object(daily_report.subprocess, "run", side_effect=fake_run):
                exit_code = daily_report.main(
                    [
                        "channel_lists/example.txt",
                        "--profile",
                        "profiles/example.md",
                        "--output-dir",
                        str(output_dir),
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertEqual(len(calls), 1)
        self.assertIn("scan.py", str(calls[0][1]))

    def test_main_returns_scan_failure_code_without_report(self):
        daily_report = load_daily_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "output"
            output_dir.mkdir()
            calls = []

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                raise daily_report.subprocess.CalledProcessError(returncode=1, cmd=cmd)

            with patch.object(daily_report.subprocess, "run", side_effect=fake_run):
                exit_code = daily_report.main(
                    [
                        "channel_lists/example.txt",
                        "--profile",
                        "profiles/example.md",
                        "--output-dir",
                        str(output_dir),
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertEqual(len(calls), 1)
        self.assertIn("scan.py", str(calls[0][1]))

    def test_html_report_uses_single_report_call_with_html_output(self):
        daily_report = load_daily_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "output"
            output_dir.mkdir()
            report_file = output_dir / "job-scan-report-2026-05-06.md"
            html_file = output_dir / "job-scan-report-2026-05-06.html"
            calls = []

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                if "scan.py" in str(cmd[1]):
                    scan_file = Path(cmd[cmd.index("--output") + 1])
                    scan_file.write_text("{}", encoding="utf-8")
                return None

            with patch.object(daily_report.subprocess, "run", side_effect=fake_run):
                exit_code = daily_report.main(
                    [
                        "channel_lists/example.txt",
                        "--profile",
                        "profiles/example.md",
                        "--output-dir",
                        str(output_dir),
                        "--report-output",
                        str(report_file),
                        "--html",
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(calls), 2)
        self.assertIn("report.py", str(calls[1][1]))
        self.assertNotIn("--html", calls[1])
        self.assertIn("--html-output", calls[1])
        self.assertIn(str(html_file), calls[1])

    def test_main_passes_state_and_feedback_flags_to_report_only(self):
        daily_report = load_daily_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "output"
            output_dir.mkdir()
            state_dir = root / ".tgcs" / "state"
            feedback_path = root / "feedback.jsonl"
            feedback_path.write_text("", encoding="utf-8")
            calls = []

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                if "scan.py" in str(cmd[1]):
                    scan_file = Path(cmd[cmd.index("--output") + 1])
                    scan_file.write_text("{}", encoding="utf-8")
                return None

            with patch.object(daily_report.subprocess, "run", side_effect=fake_run):
                exit_code = daily_report.main(
                    [
                        "channel_lists/example.txt",
                        "--profile",
                        "profiles/example.md",
                        "--output-dir",
                        str(output_dir),
                        "--state-dir",
                        str(state_dir),
                        "--state-read-only",
                        "--feedback-jsonl",
                        str(feedback_path),
                    ]
                )

        self.assertEqual(exit_code, 0)
        self.assertNotIn("--state-dir", calls[0])
        self.assertIn("--state-dir", calls[1])
        self.assertIn(str(state_dir), calls[1])
        self.assertIn("--state-read-only", calls[1])
        self.assertIn("--feedback-jsonl", calls[1])
        self.assertIn(str(feedback_path), calls[1])


if __name__ == "__main__":
    unittest.main()
