import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def load_registry_module(testcase):
    try:
        from scripts import source_registry
    except ImportError as exc:
        testcase.fail(f"scripts.source_registry should exist: {exc}")
    return source_registry


class SourceRegistryTests(unittest.TestCase):
    def test_import_list_dry_run_returns_preview_without_writing(self):
        source_registry = load_registry_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            channel_list = root / "channels.txt"
            registry_path = root / "sources.json"
            channel_list.write_text("@cointelegraph\n\n# comment\ndurov\n", encoding="utf-8")
            stdout = io.StringIO()

            with patch("sys.stdout", stdout):
                exit_code = source_registry.main(
                    [
                        "import-list",
                        str(channel_list),
                        "--source-registry",
                        str(registry_path),
                        "--format",
                        "json",
                        "--dry-run",
                    ]
                )

            payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertFalse(registry_path.exists())
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["data"]["dry_run"])
        self.assertEqual(payload["data"]["added_count"], 2)
        self.assertEqual(payload["data"]["sources"][0]["source_id"], "telegram:cointelegraph")

    def test_import_list_writes_registry_and_export_list_uses_enabled_sources(self):
        source_registry = load_registry_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            channel_list = root / "channels.txt"
            registry_path = root / "sources.json"
            export_path = root / "generated.txt"
            channel_list.write_text("cointelegraph\n123456\n", encoding="utf-8")

            import_exit = source_registry.main(
                [
                    "import-list",
                    str(channel_list),
                    "--source-registry",
                    str(registry_path),
                    "--format",
                    "json",
                ]
            )
            payload = json.loads(registry_path.read_text(encoding="utf-8"))
            payload["sources"][1]["enabled"] = False
            registry_path.write_text(json.dumps(payload), encoding="utf-8")

            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                export_exit = source_registry.main(
                    [
                        "export-list",
                        "--source-registry",
                        str(registry_path),
                        "--output",
                        str(export_path),
                        "--format",
                        "json",
                    ]
                )
            export_payload = json.loads(stdout.getvalue())
            exported_text = export_path.read_text(encoding="utf-8").strip()

        self.assertEqual(import_exit, 0)
        self.assertEqual(export_exit, 0)
        self.assertEqual(payload["schema_version"], "source_registry_v1")
        self.assertEqual(exported_text, "cointelegraph")
        self.assertEqual(export_payload["data"]["exported_count"], 1)

    def test_validate_rejects_duplicate_ids_and_invalid_fields(self):
        source_registry = load_registry_module(self)

        with tempfile.TemporaryDirectory() as tmp:
            registry_path = Path(tmp) / "sources.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "schema_version": "source_registry_v1",
                        "sources": [
                            {
                                "source_id": "telegram:cointelegraph",
                                "username": "cointelegraph",
                                "channel_id": None,
                                "label": "Cointelegraph",
                                "topics": ["market-news"],
                                "priority": "urgent",
                                "expected_language": "en",
                                "scan_window_hours": 0,
                                "enabled": True,
                                "notes": "",
                            },
                            {
                                "source_id": "telegram:cointelegraph",
                                "username": "cointelegraph",
                                "channel_id": None,
                                "label": "Duplicate",
                                "topics": [],
                                "priority": "normal",
                                "expected_language": "en",
                                "scan_window_hours": 24,
                                "enabled": True,
                                "notes": "",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            stdout = io.StringIO()

            with patch("sys.stdout", stdout):
                exit_code = source_registry.main(
                    ["validate", "--source-registry", str(registry_path), "--format", "json"]
                )

            payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 3)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "registry_invalid")
        self.assertIn("duplicate source_id", payload["error"]["message"])
        self.assertIn("priority", payload["error"]["details"]["issues"][0])


if __name__ == "__main__":
    unittest.main()
