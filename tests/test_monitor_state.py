import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts import monitor_state


class MonitorStateTests(unittest.TestCase):
    def test_init_db_is_idempotent(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row

        monitor_state.init_db(conn)
        monitor_state.init_db(conn)

        row = conn.execute(
            "SELECT version FROM schema_migrations WHERE version = ?",
            (monitor_state.STATE_SCHEMA_VERSION,),
        ).fetchone()
        self.assertIsNotNone(row)

    def test_review_card_dedupe_preserves_handled_status(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        monitor_state.init_db(conn)
        item = {
            "topic": "Exchange outage",
            "rating": "high",
            "decision_state": {"status": "new", "semantic_cluster": "cluster-1"},
            "source_message_refs": [{"channel": "cointelegraph", "id": 1}],
        }

        cards = monitor_state.upsert_review_cards(
            conn,
            profile_id="market-news",
            run_id="run-1",
            items=[item],
        )
        monitor_state.set_card_action(conn, card_id=cards[0]["card_id"], action="keep")
        cards = monitor_state.upsert_review_cards(
            conn,
            profile_id="market-news",
            run_id="run-2",
            items=[item],
        )

        self.assertEqual(cards[0]["status"], "kept")
        self.assertEqual(cards[0]["last_run_id"], "run-2")
        self.assertEqual(monitor_state.alert_candidates(cards), [])

    def test_follow_up_patch_can_apply_to_profile_file(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        monitor_state.init_db(conn)

        with tempfile.TemporaryDirectory() as tmp:
            profile_path = Path(tmp) / "profile.md"
            profile_path.write_text("# Profile\n\n## Search Rules\n1. Keep useful items.\n", encoding="utf-8")
            monitor_state.upsert_profile(
                conn,
                {"id": "market-news", "path": str(profile_path), "enabled": True},
            )
            cards = monitor_state.upsert_review_cards(
                conn,
                profile_id="market-news",
                run_id="run-1",
                items=[
                    {
                        "topic": "New rule",
                        "rating": "high",
                        "decision_state": {"status": "new"},
                        "source_message_refs": [{"channel": "source", "id": 1}],
                    }
                ],
            )
            card = monitor_state.set_card_action(
                conn,
                card_id=cards[0]["card_id"],
                action="follow_up",
                note="Prefer official incident updates.",
                profile_path=profile_path,
            )
            patch = card["profile_patch_suggestion"]
            result = monitor_state.apply_profile_patch(conn, patch_id=patch["patch_id"])

            self.assertEqual(result["status"], "applied")
            self.assertIn("## Follow-up Preferences", profile_path.read_text(encoding="utf-8"))
            self.assertIn("Prefer official incident updates.", profile_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
