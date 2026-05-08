import json
import tempfile
import unittest
from pathlib import Path


def load_report_module(testcase):
    try:
        from scripts import report
    except ImportError as exc:
        testcase.fail(f"scripts.report should exist: {exc}")
    return report


class SourceReportingTests(unittest.TestCase):
    def test_report_builds_source_summary_from_refs_and_registry(self):
        report = load_report_module(self)
        registry = {
            "schema_version": "source_registry_v1",
            "sources": [
                {
                    "source_id": "telegram:cointelegraph",
                    "username": "cointelegraph",
                    "channel_id": None,
                    "label": "Cointelegraph",
                    "topics": ["market-news"],
                    "priority": "high",
                    "expected_language": "en",
                    "scan_window_hours": 24,
                    "enabled": True,
                    "notes": "",
                }
            ],
        }
        messages = [
            {"id": 1, "channel": "cointelegraph", "date": "2026-05-08T09:00:00+00:00", "text": "A"},
            {"id": 2, "channel": "cointelegraph", "date": "2026-05-08T10:00:00+00:00", "text": "B"},
        ]
        meta = {
            "scan_date": "2026-05-08",
            "scan_window": "Last 24 hours",
            "source_health": [
                {
                    "source_id": "telegram:cointelegraph",
                    "channel": "cointelegraph",
                    "raw_count": 8,
                    "kept_count": 2,
                    "failure": None,
                    "incomplete": False,
                    "ocr_count": 0,
                }
            ],
        }
        raw_items = [
            {
                "source_message_refs": [{"channel": "cointelegraph", "id": 1}],
                "project": "Coinbase",
                "event": "Outage",
                "rating": "high",
                "why": "Decision relevant",
            },
            {
                "source_message_refs": [{"channel": "cointelegraph", "id": 2}],
                "project": "Robinhood",
                "event": "Regulation",
                "rating": "medium",
                "why": "Needs follow-up",
            },
        ]
        profile_config = report.parse_profile_config(
            """# Market Monitor

## Extraction Schema
mode: custom
top_level_key: items
dedup_fields: [project, event]
fields:
  - name: project
  - name: event
  - name: rating
  - name: why
"""
        )

        result = report.build_report(
            messages=messages,
            profile="# Market Monitor",
            raw_jobs=raw_items,
            meta=meta,
            profile_config=profile_config,
            source_registry=registry,
        )

        source = result.source_summary["sources"][0]
        self.assertEqual(source["source_id"], "telegram:cointelegraph")
        self.assertEqual(source["label"], "Cointelegraph")
        self.assertEqual(source["report_item_count"], 2)
        self.assertEqual(source["rating_counts"], {"high": 1, "medium": 1, "low": 0})
        self.assertIn("valuable_current_run", source["pruning_hints"])

    def test_origin_message_ref_deduplicates_forwarded_posts(self):
        report = load_report_module(self)
        messages = [
            {
                "id": 10,
                "channel": "aggregator_a",
                "text": "Forwarded A",
                "origin_message_ref": {"channel": "origin", "id": 77},
            },
            {
                "id": 11,
                "channel": "aggregator_b",
                "text": "Forwarded B",
                "origin_message_ref": {"channel": "origin", "id": 77},
            },
        ]
        raw_jobs = [
            {
                "source_message_refs": [{"channel": "aggregator_a", "id": 10}],
                "company": "Acme A",
                "role": "Signal A",
                "rating": "high",
            },
            {
                "source_message_refs": [{"channel": "aggregator_b", "id": 11}],
                "company": "Acme B",
                "role": "Signal B",
                "rating": "high",
            },
        ]

        jobs, duplicates_removed = report.deduplicate_jobs(raw_jobs, messages)

        self.assertEqual(duplicates_removed, 1)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["origin_message_refs"], [{"channel": "origin", "id": 77}])
        self.assertEqual(
            jobs[0]["source_message_refs"],
            [{"channel": "aggregator_a", "id": 10}, {"channel": "aggregator_b", "id": 11}],
        )

    def test_report_main_format_json_reports_output_paths(self):
        report = load_report_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "scan.jsonl"
            profile_path = root / "profile.md"
            output_path = root / "report.md"
            input_path.write_text(
                json.dumps(
                    {
                        "id": 1,
                        "channel": "cointelegraph",
                        "date": "2026-05-08T09:00:00+00:00",
                        "text": "signal",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            input_path.with_suffix(".meta.json").write_text(
                json.dumps(
                    {
                        "scan_date": "2026-05-08",
                        "scan_window": "Last 24 hours",
                        "total_messages_collected": 1,
                    }
                ),
                encoding="utf-8",
            )
            profile_path.write_text("# Profile\n", encoding="utf-8")

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
                ],
                extract_jobs_override=lambda **kwargs: [
                    {
                        "source_message_refs": [{"channel": "cointelegraph", "id": 1}],
                        "company": "Coinbase",
                        "role": "Outage",
                        "rating": "high",
                    }
                ],
            )
            output_exists = output_path.exists()

        self.assertEqual(exit_code, 0)
        self.assertTrue(output_exists)


if __name__ == "__main__":
    unittest.main()
