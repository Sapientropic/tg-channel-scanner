import json
import unittest
from pathlib import Path


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "contracts" / "profile_coach_v1.json"


class ProfileCoachContractFixtureTests(unittest.TestCase):
    def test_profile_preview_and_coach_fixtures_do_not_surface_private_fields(self):
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        surfaces = {
            "profile_template_catalog": fixture["profile_template_catalog"],
            "profile_create_preview": fixture["profile_create_preview"],
            "profile_coach_preview": fixture["profile_coach_preview"],
        }
        surfaced = json.dumps(surfaces, ensure_ascii=False, sort_keys=True)

        self.assertEqual(fixture["profile_create_preview"]["schema_version"], "desk_profile_create_preview_v1")
        self.assertEqual(fixture["profile_coach_preview"]["schema_version"], "profile_coach_preview_v1")
        for denied in fixture["denied_strings"]:
            with self.subTest(denied=denied):
                self.assertNotIn(denied, surfaced)


if __name__ == "__main__":
    unittest.main()
