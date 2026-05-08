import unittest
from pathlib import Path

from scripts.profile_schema import parse_profile_config


class ProfileTemplateTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
