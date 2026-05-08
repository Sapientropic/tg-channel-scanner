import json
import tempfile
import unittest
from pathlib import Path


def load_state_store(testcase):
    try:
        from scripts import state_store
    except ImportError as exc:
        testcase.fail(f"scripts.state_store should exist: {exc}")
    return state_store


class StateStoreTests(unittest.TestCase):
    def test_missing_state_loads_empty_item_memory(self):
        state_store = load_state_store(self)

        with tempfile.TemporaryDirectory() as tmp:
            state = state_store.load_item_memory(Path(tmp))

        self.assertEqual(state["schema_version"], "item_memory_v1")
        self.assertEqual(state["items"], {})

    def test_save_item_memory_is_atomic_and_never_requires_raw_text(self):
        state_store = load_state_store(self)

        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            state = state_store.default_item_memory()
            state["items"]["market-news:coinbase-outage"] = {
                "item_key": "market-news:coinbase-outage",
                "profile_key": "profile:market-news",
                "source_message_refs": [{"channel": "cointelegraph", "id": 101}],
                "first_seen_at": "2026-05-08T09:00:00Z",
                "last_seen_at": "2026-05-08T09:00:00Z",
                "seen_count": 1,
                "rating_history": [{"at": "2026-05-08T09:00:00Z", "rating": "high"}],
                "fingerprint": "abc123",
                "feedback_counts": {"keep": 1},
            }

            state_store.save_item_memory(state_dir, state)
            loaded = state_store.load_item_memory(state_dir)
            raw = state_store.item_memory_path(state_dir).read_text(encoding="utf-8")

        self.assertEqual(loaded["items"]["market-news:coinbase-outage"]["seen_count"], 1)
        self.assertNotIn("raw message text", raw)
        self.assertFalse(list(Path(tmp).glob("*.tmp")) if Path(tmp).exists() else [])

    def test_corrupt_or_wrong_schema_state_fails_loudly(self):
        state_store = load_state_store(self)

        with tempfile.TemporaryDirectory() as tmp:
            state_dir = Path(tmp)
            state_store.item_memory_path(state_dir).parent.mkdir(parents=True, exist_ok=True)
            state_store.item_memory_path(state_dir).write_text("{not json", encoding="utf-8")

            with self.assertRaises(state_store.StateStoreError):
                state_store.load_item_memory(state_dir)

            state_store.item_memory_path(state_dir).write_text(
                json.dumps({"schema_version": "old", "items": {}}),
                encoding="utf-8",
            )
            with self.assertRaises(state_store.StateStoreError):
                state_store.load_item_memory(state_dir)


if __name__ == "__main__":
    unittest.main()
