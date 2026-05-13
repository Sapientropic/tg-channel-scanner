import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import monitor, monitor_state


class MonitorFeedbackExportTests(unittest.TestCase):
    def test_feedback_export_writes_report_reusable_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / ".tgcs" / "tgcs.db"
            output = root / "output" / "dashboard-feedback.jsonl"
            conn = monitor_state.connect(db_path)
            try:
                cards = monitor_state.upsert_review_cards(
                    conn,
                    profile_id="jobs-fast",
                    run_id="run-1",
                    items=[
                        {
                            "topic": "TypeScript role",
                            "rating": "high",
                            "decision_state": {"status": "new", "semantic_cluster": "feedback-cli"},
                            "source_message_refs": [{"channel": "jobs", "id": 1}],
                        }
                    ],
                )
                monitor_state.set_card_action(conn, card_id=cards[0]["card_id"], action="keep", note="private note")
            finally:
                conn.close()

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                exit_code = monitor.main(
                    [
                        "feedback-export",
                        "--db",
                        str(db_path),
                        "--output",
                        str(output),
                        "--format",
                        "json",
                    ]
                )

            payload = json.loads(stdout.getvalue())
            rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["feedback_count"], 1)
        self.assertEqual(rows[0]["feedback"], "keep")
        self.assertEqual(rows[0]["note"], "")

    def test_feedback_export_default_output_is_grouped(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / ".tgcs" / "tgcs.db"
            conn = monitor_state.connect(db_path)
            conn.close()

            stdout = io.StringIO()
            with patch.object(monitor, "PROJECT_ROOT", root):
                with patch("sys.stdout", stdout):
                    exit_code = monitor.main(["feedback-export", "--db", str(db_path), "--format", "json"])

            payload = json.loads(stdout.getvalue())
            output = root / "output" / "feedback" / "review-feedback.jsonl"
            output_exists = output.exists()

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["output_path"], "output/feedback/review-feedback.jsonl")
        self.assertTrue(output_exists)



if __name__ == "__main__":
    unittest.main()
