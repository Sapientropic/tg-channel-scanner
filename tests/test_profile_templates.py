import unittest
from pathlib import Path

from scripts.profile_schema import parse_profile_config


class ProfileTemplateTests(unittest.TestCase):
    STANDARD_SECTIONS = {
        "Basic Info",
        "Search Rules",
        "Rejection Rules",
        "Prefilter Tuning",
        "Good Examples",
        "Bad Examples",
        "Extraction Schema",
        "Extraction Prompt",
        "Report Preferences",
        "Follow-up Preferences",
        "Report Labels",
    }

    def test_builtin_profile_templates_exist_and_parse(self):
        template_dir = Path("profiles/templates")
        expected = {
            "jobs.md",
            "airdrops.md",
            "market-news.md",
            "research-leads.md",
            "competitor-monitoring.md",
        }

        self.assertEqual(expected, {path.name for path in template_dir.glob("*.md")})

        for path in template_dir.glob("*.md"):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                config = parse_profile_config(text)
                self.assertTrue(config.labels.report_title)
                self.assertTrue(config.labels.output_filename.endswith(".md"))
                self.assertTrue(config.mode.fields)

    def test_builtin_templates_meet_profile_coach_contract(self):
        template_dir = Path("profiles/templates")

        for path in template_dir.glob("*.md"):
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                normalized = " ".join(text.casefold().split())
                sections = {
                    line.removeprefix("##").strip()
                    for line in text.splitlines()
                    if line.startswith("## ")
                }
                self.assertTrue(self.STANDARD_SECTIONS.issubset(sections))
                self.assertRegex(normalized, r"\b(source_message_refs|source refs|source references)\b")
                self.assertIn("section_high", normalized)
                self.assertIn("section_medium", normalized)
                self.assertIn("section_low", normalized)
                rejection_body = text.split("## Rejection Rules", 1)[1].split("##", 1)[0].casefold()
                self.assertIn("reject", rejection_body)
                self.assertRegex(rejection_body, r"do not match|do not include|never match|not a match")
                self.assertRegex(rejection_body, r"\b(skip|exclude|reject|avoid)\b")

    def test_jobs_profile_uses_compact_fast_alert_schema(self):
        text = Path("profiles/templates/jobs.md").read_text(encoding="utf-8")
        normalized_text = " ".join(text.casefold().split())
        config = parse_profile_config(text)
        field_names = {field.name for field in config.mode.fields}
        opportunity_type = next(field for field in config.mode.fields if field.name == "opportunity_type")

        self.assertEqual(config.mode.top_level_key, "items")
        self.assertEqual(config.mode.dedup_fields, ["company", "role"])
        self.assertIn("opportunity_type", field_names)
        self.assertIn("role", field_names)
        self.assertIn("apply_url", field_names)
        self.assertIn("urgency_reason", field_names)
        self.assertNotIn("stack", field_names)
        self.assertIn("contract", opportunity_type.values)
        self.assertIn("mini_app_ton_project", opportunity_type.values)
        self.assertIn("candidate_profile", opportunity_type.values)
        self.assertIn("non_vacancy", opportunity_type.values)
        self.assertIn("developer opportunity", normalized_text)
        self.assertIn("mini apps", normalized_text)
        self.assertIn("ton", normalized_text)
        self.assertIn("freelance", normalized_text)
        self.assertIn("budget", normalized_text)
        self.assertIn("candidate cv", normalized_text)
        self.assertIn("not an employer/recruiter/client opening", normalized_text)
        self.assertIn("frontend-focused", normalized_text)
        self.assertIn("backend-only", normalized_text)
        self.assertIn("at most 8 items", normalized_text)
        self.assertIn("do not copy full job descriptions", normalized_text)


if __name__ == "__main__":
    unittest.main()
