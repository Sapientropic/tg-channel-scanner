import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .helpers import load_report_module


class ReportStateIntegrationTests(unittest.TestCase):
    def test_report_main_state_dir_persists_seen_state_and_json_summary(self):
        report = load_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "scan.jsonl"
            profile_path = root / "profile.md"
            items_path = root / "items.json"
            output_path = root / "report.md"
            state_dir = root / ".tgcs" / "state"
            input_path.write_text(
                json.dumps(
                    {
                        "id": 101,
                        "channel": "cointelegraph",
                        "date": "2026-05-08T09:00:00+00:00",
                        "text": "Coinbase outage affects trading.",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            input_path.with_suffix(".meta.json").write_text(
                json.dumps({"scan_date": "2026-05-08", "scan_window": "Last 24 hours"}),
                encoding="utf-8",
            )
            profile_path.write_text(
                """# Market Watch

## Extraction Schema
mode: custom
top_level_key: items
dedup_fields: [topic, event]
fields:
  - name: topic
  - name: event
  - name: rating
    values: [high, medium, low]
  - name: why
""",
                encoding="utf-8",
            )
            items_path.write_text(
                json.dumps(
                    {
                        "schema_version": "semantic_items_v1",
                        "items": [
                            {
                                "source_message_refs": [{"channel": "cointelegraph", "id": 101}],
                                "topic": "Coinbase",
                                "event": "Exchange outage",
                                "rating": "high",
                                "why": "Decision-relevant operational risk.",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            stdout_first = io.StringIO()
            stdout_second = io.StringIO()

            with patch("sys.stdout", stdout_first):
                first_exit = report.main(
                    [
                        "--input",
                        str(input_path),
                        "--profile",
                        str(profile_path),
                        "--items-json",
                        str(items_path),
                        "--output",
                        str(output_path),
                        "--state-dir",
                        str(state_dir),
                        "--format",
                        "json",
                    ]
                )
            with patch("sys.stdout", stdout_second):
                second_exit = report.main(
                    [
                        "--input",
                        str(input_path),
                        "--profile",
                        str(profile_path),
                        "--items-json",
                        str(items_path),
                        "--output",
                        str(output_path),
                        "--state-dir",
                        str(state_dir),
                        "--format",
                        "json",
                    ]
                )

            first_payload = json.loads(stdout_first.getvalue())
            second_payload = json.loads(stdout_second.getvalue())
            state_text = (state_dir / "item-memory.json").read_text(encoding="utf-8")

        self.assertEqual(first_exit, 0)
        self.assertEqual(second_exit, 0)
        self.assertEqual(first_payload["data"]["state_summary"]["new"], 1)
        self.assertEqual(first_payload["data"]["items"][0]["decision_state"]["status"], "new")
        self.assertEqual(second_payload["data"]["state_summary"]["seen"], 1)
        self.assertEqual(second_payload["data"]["items"][0]["decision_state"]["status"], "seen")
        self.assertNotIn("Coinbase outage affects trading", state_text)


    def test_report_main_state_read_only_does_not_write_memory_file(self):
        report = load_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "scan.jsonl"
            profile_path = root / "profile.md"
            items_path = root / "items.json"
            state_dir = root / ".tgcs" / "state"
            input_path.write_text(
                json.dumps(
                    {
                        "id": 101,
                        "channel": "cointelegraph",
                        "date": "2026-05-08T09:00:00+00:00",
                        "text": "Coinbase outage affects trading.",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            profile_path.write_text(
                """# Market Watch

## Extraction Schema
mode: custom
top_level_key: items
dedup_fields: [topic, event]
fields:
  - name: topic
  - name: event
  - name: rating
    values: [high, medium, low]
  - name: why
""",
                encoding="utf-8",
            )
            items_path.write_text(
                json.dumps(
                    {
                        "schema_version": "semantic_items_v1",
                        "items": [
                            {
                                "source_message_refs": [{"channel": "cointelegraph", "id": 101}],
                                "topic": "Coinbase",
                                "event": "Exchange outage",
                                "rating": "high",
                                "why": "Decision-relevant operational risk.",
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
                        "--state-dir",
                        str(state_dir),
                        "--state-read-only",
                        "--format",
                        "json",
                    ]
                )
            payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["data"]["state_summary"]["new"], 1)
        self.assertFalse((state_dir / "item-memory.json").exists())



if __name__ == "__main__":
    unittest.main()
