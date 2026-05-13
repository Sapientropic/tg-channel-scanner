import tempfile
import unittest
import json
from io import BytesIO
from http import HTTPStatus
from pathlib import Path
from unittest.mock import patch

from scripts import dashboard_server, monitor_state


class DashboardArtifactServingTests(unittest.TestCase):
    def test_markdown_report_artifact_renders_as_mobile_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.md"
            report.write_text(
                "# Market News Signal Brief\n\n"
                "A readable report with **strong signal**.\n\n"
                "| Source | Count |\n| --- | --- |\n| Telegram | 2 |\n\n"
                "- Open [source](https://example.com)\n",
                encoding="utf-8",
            )

            body = dashboard_server.render_markdown_artifact(report).decode("utf-8")

        self.assertIn("<meta name=\"viewport\"", body)
        self.assertIn("<h1>Market News Signal Brief</h1>", body)
        self.assertIn("<strong>strong signal</strong>", body)
        self.assertIn("<table>", body)
        self.assertIn('href="https://example.com"', body)


    def test_serve_markdown_artifact_over_http_as_rendered_html(self):
        class FakeHandler:
            status = None
            headers = {}
            wfile = BytesIO()

            def send_response(self, status):
                self.status = status

            def send_header(self, key, value):
                self.headers[key] = value

            def end_headers(self):
                pass

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "output" / "runs" / "run-1" / "report.md"
            report.parent.mkdir(parents=True)
            report.write_text("# Report\n\nBody", encoding="utf-8")

            with patch.object(dashboard_server, "PROJECT_ROOT", root):
                handler = FakeHandler()
                dashboard_server.DashboardHandler._serve_artifact(handler, "output/runs/run-1/report.md")

        self.assertEqual(handler.status, HTTPStatus.OK.value)
        self.assertEqual(handler.headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn(b"<h1>Report</h1>", handler.wfile.getvalue())


    def test_serve_html_report_artifact_injects_mobile_patch(self):
        class FakeHandler:
            status = None
            headers = {}
            wfile = BytesIO()

            def send_response(self, status):
                self.status = status

            def send_header(self, key, value):
                self.headers[key] = value

            def end_headers(self):
                pass

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "output" / "runs" / "run-1" / "report.html"
            report.parent.mkdir(parents=True)
            report.write_text(
                "<html><head><title>Report</title></head><body><h1 class=\"report-title\">Long Report</h1></body></html>",
                encoding="utf-8",
            )

            with patch.object(dashboard_server, "PROJECT_ROOT", root):
                handler = FakeHandler()
                dashboard_server.DashboardHandler._serve_artifact(handler, "output/runs/run-1/report.html")

        self.assertEqual(handler.status, HTTPStatus.OK.value)
        self.assertEqual(handler.headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn(b"data-dashboard-report-mobile-patch", handler.wfile.getvalue())


    def test_serve_artifact_allows_demo_report_html(self):
        class FakeHandler:
            status = None
            headers = {}
            wfile = BytesIO()

            def send_response(self, status):
                self.status = status

            def send_header(self, key, value):
                self.headers[key] = value

            def end_headers(self):
                pass

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "output" / "demo-report.html"
            report.parent.mkdir(parents=True)
            report.write_text("<html><body><h1>Demo Report</h1></body></html>", encoding="utf-8")

            with patch.object(dashboard_server, "PROJECT_ROOT", root):
                handler = FakeHandler()
                dashboard_server.DashboardHandler._serve_artifact(handler, "output/demo-report.html")

        self.assertEqual(handler.status, HTTPStatus.OK.value)
        self.assertEqual(handler.headers["Content-Type"], "text/html; charset=utf-8")
        self.assertIn(b"Demo Report", handler.wfile.getvalue())


    def test_write_feedback_export_writes_note_free_dashboard_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / ".tgcs" / "tgcs.db"
            output_path = root / "output" / "dashboard-feedback.jsonl"
            conn = monitor_state.connect(db_path)
            try:
                cards = monitor_state.upsert_review_cards(
                    conn,
                    profile_id="jobs-fast",
                    run_id="run-1",
                    items=[
                        {
                            "topic": "Contract role",
                            "rating": "high",
                            "source_message_refs": [{"channel": "jobs", "id": 1}],
                        }
                    ],
                )
                monitor_state.set_card_action(conn, card_id=cards[0]["card_id"], action="keep", note="private")

                with patch.object(dashboard_server, "PROJECT_ROOT", root):
                    result = dashboard_server.write_feedback_export(conn, output_path=output_path)
            finally:
                conn.close()

            rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(result["feedback_count"], 1)
        self.assertEqual(rows[0]["feedback"], "keep")
        self.assertEqual(rows[0]["note"], "")


    def test_write_feedback_export_defaults_to_grouped_feedback_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / ".tgcs" / "tgcs.db"
            conn = monitor_state.connect(db_path)
            try:
                with patch.object(dashboard_server, "PROJECT_ROOT", root):
                    result = dashboard_server.write_feedback_export(conn)
            finally:
                conn.close()

            output_path = root / "output" / "feedback" / "review-feedback.jsonl"
            output_exists = output_path.exists()

        self.assertEqual(result["output_path"], "output/feedback/review-feedback.jsonl")
        self.assertTrue(output_exists)


    def test_write_feedback_export_rejects_path_outside_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            db_path = root / ".tgcs" / "tgcs.db"
            outside_path = Path(tmp) / "private" / "review-feedback.jsonl"
            conn = monitor_state.connect(db_path)
            try:
                with patch.object(dashboard_server, "PROJECT_ROOT", root):
                    with self.assertRaises(ValueError) as raised:
                        dashboard_server.write_feedback_export(conn, output_path=outside_path)
                    latest = monitor_state.latest_feedback_export(conn)
            finally:
                conn.close()

        self.assertEqual(str(raised.exception), "feedback_export_path_outside_project")
        self.assertFalse(outside_path.exists())
        self.assertIsNone(latest)


    def test_serve_artifact_rejects_raw_scan_over_http_handler(self):
        class FakeHandler:
            status = None
            payload = None

            def _json(self, status, payload):
                self.status = status
                self.payload = payload

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scan = root / "output" / "runs" / "run-1" / "scan.jsonl"
            scan.parent.mkdir(parents=True)
            scan.write_text('{"text":"raw"}\n', encoding="utf-8")

            with patch.object(dashboard_server, "PROJECT_ROOT", root):
                handler = FakeHandler()
                dashboard_server.DashboardHandler._serve_artifact(handler, "output/runs/run-1/scan.jsonl")

        self.assertEqual(handler.status, HTTPStatus.NOT_FOUND)
        self.assertEqual(handler.payload["error"], "artifact_type_not_report")



if __name__ == "__main__":
    unittest.main()
