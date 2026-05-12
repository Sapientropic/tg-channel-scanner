import json
import sqlite3
import unittest
from pathlib import Path

from scripts import monitor_state


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "contracts" / "review-card-privacy-item.json"


class ContractPrivacyFixtureTests(unittest.TestCase):
    def test_review_card_privacy_fixture_stays_out_of_state_surfaces(self):
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        monitor_state.init_db(conn)

        cards = monitor_state.upsert_review_cards(
            conn,
            profile_id="jobs-fast",
            run_id="run-fixture",
            items=[fixture["review_item"]],
        )
        monitor_state.set_card_action(
            conn,
            card_id=cards[0]["card_id"],
            action="keep",
            note="PRIVATE_NOTE_SHOULD_NOT_RENDER",
        )

        stored_item = conn.execute(
            "SELECT item_json FROM review_cards WHERE card_id = ?",
            (cards[0]["card_id"],),
        ).fetchone()["item_json"]
        surfaces = {
            "stored_item": json.loads(stored_item),
            "review_card": monitor_state.get_review_card(conn, cards[0]["card_id"]),
            "dashboard_snapshot": monitor_state.dashboard_snapshot(conn),
            "feedback_export": monitor_state.export_feedback_entries(conn),
        }
        surfaced_text = json.dumps(surfaces, ensure_ascii=False, sort_keys=True)

        self.assertIn("Senior TypeScript Engineer", surfaced_text)
        self.assertIn("Strong TypeScript and React match.", surfaced_text)
        for denied in [*fixture["denied_strings"], "PRIVATE_NOTE_SHOULD_NOT_RENDER"]:
            with self.subTest(denied=denied):
                self.assertNotIn(denied, surfaced_text)


if __name__ == "__main__":
    unittest.main()
