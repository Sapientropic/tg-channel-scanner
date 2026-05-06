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

    def test_main_runs_scan_then_report_with_latest_scan_file(self):
        daily_report = load_daily_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "output"
            output_dir.mkdir()
            scan_file = output_dir / "scan_20260506_080000.jsonl"
            report_file = output_dir / "job-scan-report-2026-05-06.md"
            calls = []

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                if "scan.py" in str(cmd[1]):
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
        self.assertIn(str(scan_file), calls[1])
        self.assertIn(str(report_file), calls[1])
        self.assertIn("Next scan scheduled for tomorrow.", calls[1])


if __name__ == "__main__":
    unittest.main()
