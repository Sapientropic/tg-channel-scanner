import unittest

from .helpers import load_report_module, sample_extracted_jobs, sample_messages


class ReportMarkdownTests(unittest.TestCase):
    def test_build_report_renders_fixed_sections_and_program_stats(self):
        report = load_report_module(self)
        meta = {
            "scan_date": "2026-05-06",
            "scan_window": "Last 24 hours",
            "channel_count": 17,
            "channels": ["React Job", "JavaScript Job", "TypeScript Job Offers"],
            "total_messages_collected": 5,
        }

        result = report.build_report(
            messages=sample_messages(),
            profile="Aleksei Vlasov\nSenior Frontend Developer\nReact TypeScript remote",
            raw_jobs=sample_extracted_jobs(),
            meta=meta,
            next_scan_note="Next scan scheduled for tomorrow.",
        )

        self.assertEqual(result.stats["matches"], 3)
        self.assertEqual(result.stats["duplicates_removed"], 1)
        self.assertEqual(result.stats["non_relevant_filtered_out"], 1)
        self.assertEqual(result.stats["high"], 1)
        self.assertEqual(result.stats["medium"], 1)
        self.assertEqual(result.stats["low"], 1)
        self.assertIn("# Job Scan Report", result.markdown)
        self.assertIn("**Channels scanned**: 17", result.markdown)
        self.assertIn("## Highly Recommended", result.markdown)
        self.assertIn("## Worth Investigating", result.markdown)
        self.assertIn("## Low Priority", result.markdown)
        self.assertIn("ООО Исходный код", result.markdown)
        self.assertIn("React Job / JavaScript Job", result.markdown)
        self.assertIn("| Duplicates removed | 1 |", result.markdown)
        self.assertIn("*Generated automatically. Next scan scheduled for tomorrow.*", result.markdown)


    def test_missing_meta_keeps_running_and_marks_report_as_needing_confirmation(self):
        report = load_report_module(self)

        result = report.build_report(
            messages=sample_messages()[:1],
            profile="Senior Frontend Developer",
            raw_jobs=sample_extracted_jobs()[:1],
            meta=None,
        )

        self.assertIn("⚠️ Needs confirmation", result.markdown)
        self.assertIn("## Diagnostics", result.markdown)
        self.assertEqual(result.stats["total_messages_scanned"], 1)


    def test_markdown_report_includes_feedback_jsonl_schema(self):
        report = load_report_module(self)

        result = report.build_report(
            messages=sample_messages()[:1],
            profile="Senior Frontend Developer",
            raw_jobs=sample_extracted_jobs()[:1],
            meta={"scan_date": "2026-05-06", "scan_window": "Last 24 hours"},
        )

        self.assertIn("## Feedback", result.markdown)
        self.assertIn("schema_version", result.markdown)
        self.assertIn("false_negative", result.markdown)


    def test_build_report_with_state_marks_decision_state_and_negative_evidence(self):
        report = load_report_module(self)
        from scripts import state_store

        profile = """# Market Watch

## Extraction Schema
mode: custom
top_level_key: items
dedup_fields: [topic, event]
fields:
  - name: source_message_refs
    type: list
  - name: topic
  - name: event
  - name: rating
    values: [high, medium, low]
  - name: why
  - name: negative_evidence
"""
        profile_config = report.parse_profile_config(profile)

        result = report.build_report(
            messages=[
                {
                    "id": 101,
                    "channel": "cointelegraph",
                    "date": "2026-05-08T09:00:00+00:00",
                    "text": "Coinbase outage affects trading.",
                }
            ],
            profile=profile,
            raw_jobs=[
                {
                    "source_message_refs": [{"channel": "cointelegraph", "id": 101}],
                    "topic": "Coinbase",
                    "event": "Exchange outage",
                    "rating": "high",
                    "why": "Decision-relevant operational risk.",
                    "negative_evidence": "No official postmortem yet.",
                }
            ],
            meta={"scan_date": "2026-05-08", "scan_window": "Last 24 hours"},
            profile_config=profile_config,
            state=state_store.default_item_memory(),
            state_observed_at="2026-05-08T09:00:00Z",
        )

        self.assertEqual(result.state_summary["new"], 1)
        self.assertEqual(result.jobs[0]["decision_state"]["status"], "new")
        self.assertIn("Decision state: New", result.markdown)
        self.assertIn("Negative evidence", result.markdown)


    def test_custom_markdown_render_uses_profile_action_mapping(self):
        report = load_report_module(self)
        profile = """# Custom watchlist

## Extraction Schema
mode: custom
top_level_key: items
dedup_fields: [project, event]
fields:
  - name: project
    required: true
  - name: event
  - name: rating
    values: [high, medium, low]
  - name: action
    values: ["Join now", "Review source", "Skip"]
  - name: why
"""
        profile_config = report.parse_profile_config(profile)

        rendered = report.render_job(
            {
                "project": "Example Protocol",
                "event": "Quest opens",
                "rating": "high",
                "why": "Fresh campaign with explicit source.",
            },
            1,
            profile_config,
        )

        self.assertIn("**Action**: **Join now**", rendered)


    def test_markdown_title_uses_role_when_company_is_placeholder(self):
        report = load_report_module(self)
        profile = """# Developer Opportunities

## Extraction Schema
mode: custom
top_level_key: items
dedup_fields: [company, role]
fields:
  - name: company
  - name: role
    required: true
  - name: rating
    values: [high, medium, low]
"""
        profile_config = report.parse_profile_config(profile)

        rendered = report.render_job(
            {
                "company": "Unknown",
                "role": "AI Engineer",
                "rating": "high",
                "why": "Strong fit.",
            },
            1,
            profile_config,
        )

        self.assertIn("### 1. AI Engineer", rendered)
        self.assertNotIn("### 1. Unknown", rendered)


    def test_markdown_field_labels_are_human_readable(self):
        report = load_report_module(self)
        profile = """# Developer Opportunities

## Extraction Schema
mode: custom
top_level_key: items
dedup_fields: [company, role]
fields:
  - name: company
  - name: role
  - name: apply_url
  - name: urgency_reason
  - name: rating
    values: [high, medium, low]
"""
        profile_config = report.parse_profile_config(profile)

        rendered = report.render_job(
            {
                "company": "Example Co",
                "role": "AI Engineer",
                "apply_url": "https://example.com/apply",
                "urgency_reason": "Fresh post.",
                "rating": "high",
            },
            1,
            profile_config,
        )

        self.assertIn("**Apply URL**", rendered)
        self.assertIn("**Urgency Reason**", rendered)
        self.assertNotIn("Apply_Url", rendered)
        self.assertNotIn("Urgency_Reason", rendered)



if __name__ == "__main__":
    unittest.main()
