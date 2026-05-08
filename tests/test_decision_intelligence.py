import unittest


def load_decision_module(testcase):
    try:
        from scripts import decision_intelligence, state_store
    except ImportError as exc:
        testcase.fail(f"decision intelligence modules should exist: {exc}")
    return decision_intelligence, state_store


def profile_config():
    from scripts.profile_schema import parse_profile_config

    return parse_profile_config(
        """# Market Watch

## Extraction Schema
mode: custom
top_level_key: items
dedup_fields: [topic, event]
fields:
  - name: topic
  - name: event
  - name: market_impact
  - name: urgency
  - name: deadline_or_time
  - name: rating
    values: [high, medium, low]
  - name: why
  - name: negative_evidence
"""
    )


def market_item(**overrides):
    item = {
        "source_message_refs": [{"channel": "cointelegraph", "id": 101}],
        "topic": "Coinbase",
        "event": "Exchange outage",
        "market_impact": "Trading access degraded",
        "urgency": "today",
        "deadline_or_time": "2026-05-20",
        "rating": "high",
        "why": "Decision-relevant operational risk.",
        "negative_evidence": "No official postmortem yet.",
    }
    item.update(overrides)
    return item


class DecisionIntelligenceTests(unittest.TestCase):
    def test_first_second_and_third_seen_states_are_new_seen_recurring(self):
        decision_intelligence, state_store = load_decision_module(self)
        state = state_store.default_item_memory()
        config = profile_config()

        first, state, summary = decision_intelligence.enrich_items(
            [market_item()],
            profile="# Market Watch",
            profile_config=config,
            state=state,
            observed_at="2026-05-08T09:00:00Z",
        )
        second, state, _ = decision_intelligence.enrich_items(
            [market_item()],
            profile="# Market Watch",
            profile_config=config,
            state=state,
            observed_at="2026-05-09T09:00:00Z",
        )
        third, state, _ = decision_intelligence.enrich_items(
            [market_item()],
            profile="# Market Watch",
            profile_config=config,
            state=state,
            observed_at="2026-05-10T09:00:00Z",
        )

        self.assertEqual(first[0]["decision_state"]["status"], "new")
        self.assertEqual(second[0]["decision_state"]["status"], "seen")
        self.assertEqual(third[0]["decision_state"]["status"], "recurring")
        self.assertEqual(summary["new"], 1)
        stored = next(iter(state["items"].values()))
        self.assertEqual(stored["seen_count"], 3)
        self.assertEqual([row["rating"] for row in stored["rating_history"]], ["high", "high", "high"])

    def test_changed_and_expired_items_are_explained_without_total_score(self):
        decision_intelligence, state_store = load_decision_module(self)
        state = state_store.default_item_memory()
        config = profile_config()

        _, state, _ = decision_intelligence.enrich_items(
            [market_item()],
            profile="# Market Watch",
            profile_config=config,
            state=state,
            observed_at="2026-05-08T09:00:00Z",
        )
        changed, state, summary = decision_intelligence.enrich_items(
            [
                market_item(
                    market_impact="Trading access restored",
                    deadline_or_time="2026-05-07",
                    rating="medium",
                )
            ],
            profile="# Market Watch",
            profile_config=config,
            state=state,
            observed_at="2026-05-10T09:00:00Z",
        )

        decision_state = changed[0]["decision_state"]
        self.assertEqual(decision_state["schema_version"], "decision_state_v1")
        self.assertEqual(decision_state["status"], "expired")
        self.assertIn("changed", decision_state["signals"])
        self.assertIn("negative_evidence", decision_state["explanations"])
        self.assertNotIn("score", decision_state)
        self.assertEqual(summary["expired"], 1)

    def test_feedback_entries_update_counts_without_persisting_notes(self):
        decision_intelligence, state_store = load_decision_module(self)
        state = state_store.default_item_memory()

        _, state, _ = decision_intelligence.enrich_items(
            [market_item()],
            profile="# Market Watch",
            profile_config=profile_config(),
            state=state,
            feedback_entries=[
                {
                    "source_message_refs": [{"channel": "cointelegraph", "id": 101}],
                    "feedback": "false_positive",
                    "note": "raw private note should not persist",
                    "item_title": "Coinbase - Exchange outage",
                }
            ],
            observed_at="2026-05-08T09:00:00Z",
        )
        stored = next(iter(state["items"].values()))

        self.assertEqual(stored["feedback_counts"], {"false_positive": 1})
        self.assertNotIn("note", stored)
        self.assertNotIn("raw private note", str(state))


if __name__ == "__main__":
    unittest.main()
