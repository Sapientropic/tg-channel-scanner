import json
import unittest
from pathlib import Path

from scripts import report


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "contracts" / "agent_extraction_request_v1.minimal.json"


class ReportContractTests(unittest.TestCase):
    def test_agent_extraction_request_uses_minimized_scan_meta_and_messages(self):
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        profile = "# Job Profile\nRemote TypeScript roles only."
        request = report.build_agent_extraction_request(
            messages=[
                {
                    "channel": "jobs_a",
                    "id": 10,
                    "date": "2026-05-09T12:00:00Z",
                    "text": "Senior React remote role. Contact @hr.",
                    "origin_url": "https://t.me/original_jobs/10",
                    "origin_channel": "original_jobs",
                    "origin_message_ref": {"channel": "original_jobs", "id": 10},
                    "message_ref": {"channel": "jobs_a", "id": 10},
                    "sender_id": -100123,
                    "media_type": "MessageMediaPhoto",
                    "has_photo": True,
                    "monitor_prefilter": {"matched_keywords": ["react"]},
                }
            ],
            profile=profile,
            meta={
                "scan_date": "2026-05-09",
                "scan_started_at": "2026-05-09T12:25:31Z",
                "scan_completed_at": "2026-05-09T12:27:31Z",
                "scan_window": "Last 2 hours",
                "cutoff": "2026-05-09T10:25:31Z",
                "channel_count": 68,
                "total_messages_collected": 23,
                "failure_count": 0,
                "incomplete_count": 0,
                "ocr_enabled": False,
                "ocr_count": 0,
                "output_path": r"E:\workspace\output\runs\run-1\scan.jsonl",
                "errors_path": r"E:\workspace\output\runs\run-1\scan.errors.log",
                "source_registry_path": r"E:\workspace\output\runs\run-1\source-registry.filtered.json",
                "source_health": [
                    {
                        "channel": "jobs_a",
                        "raw_count": 9,
                        "kept_count": 7,
                        "oldest_message_at": "2026-05-09T11:00:00Z",
                    }
                ],
            },
            input_path=Path("scan.jsonl"),
            profile_path=Path("profile.md"),
            output_path="report.md",
            items_output_path=Path("extracted-items.json"),
            max_messages=10,
            profile_config=report.parse_profile_config(profile),
        )

        self.assertEqual(request["schema_version"], fixture["schema_version"])
        self.assertEqual(request["scan_meta"], fixture["scan_meta"])
        self.assertEqual(request["selected_messages"], fixture["selected_messages"])
        for key in fixture["denied_scan_meta_keys"]:
            with self.subTest(scan_meta_key=key):
                self.assertNotIn(key, request["scan_meta"])
        for message in request["selected_messages"]:
            for key in fixture["denied_message_keys"]:
                with self.subTest(message_key=key):
                    self.assertNotIn(key, message)
        request_text = json.dumps(
            {
                "scan_meta": request["scan_meta"],
                "selected_messages": request["selected_messages"],
                "user_prompt": request["user_prompt"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        for denied in fixture["denied_strings"]:
            with self.subTest(denied=denied):
                self.assertNotIn(denied, request_text)


if __name__ == "__main__":
    unittest.main()
