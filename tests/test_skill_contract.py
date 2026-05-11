import unittest
from pathlib import Path


class SkillContractTests(unittest.TestCase):
    def test_root_skill_declares_agent_safe_workflow(self):
        skill_path = Path("SKILL.md")
        self.assertTrue(skill_path.exists(), "Root SKILL.md should make the repo agent-installable")

        text = skill_path.read_text(encoding="utf-8")

        self.assertIn("name: t-sense", text)
        self.assertIn("description:", text)
        self.assertIn("doctor.py", text)
        self.assertIn("--format json", text)
        self.assertIn("source_registry.py", text)
        self.assertIn("Do not perform interactive Telegram login", text)

    def test_agent_metadata_exists(self):
        metadata_path = Path("agents/openai.yaml")
        self.assertTrue(metadata_path.exists())
        text = metadata_path.read_text(encoding="utf-8")
        self.assertIn("display_name:", text)
        self.assertIn("default_prompt:", text)

    def test_agent_cli_contract_doc_exists(self):
        doc_path = Path("docs/agent-cli-contract.md")
        self.assertTrue(doc_path.exists())
        text = doc_path.read_text(encoding="utf-8")
        self.assertIn("agent_envelope_v1", text)
        self.assertIn("source_registry_v1", text)
        self.assertIn("Exit Codes", text)


if __name__ == "__main__":
    unittest.main()
