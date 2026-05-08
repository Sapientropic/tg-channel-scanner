import asyncio
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


def load_module(testcase, name: str):
    try:
        module = __import__(f"scripts.{name}", fromlist=[name])
    except ImportError as exc:
        testcase.fail(f"scripts.{name} should exist: {exc}")
    return module


class AgentNativeCliTests(unittest.TestCase):
    def test_doctor_format_json_wraps_checks_in_envelope_with_registry(self):
        doctor = load_module(self, "doctor")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "sources.json"
            profile_path = root / "profile.md"
            output_dir = root / "output"
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
                                "priority": "normal",
                                "expected_language": "en",
                                "scan_window_hours": 24,
                                "enabled": True,
                                "notes": "",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            profile_path.write_text("# Profile\n", encoding="utf-8")
            stdout = io.StringIO()

            with patch.dict(
                "os.environ",
                {
                    "TELEGRAM_API_ID": "123",
                    "TELEGRAM_API_HASH": "hash",
                    "DEEPSEEK_API_KEY": "sk-test",
                },
                clear=True,
            ):
                with patch("sys.stdout", stdout):
                    exit_code = doctor.main(
                        [
                            "--source-registry",
                            str(registry_path),
                            "--profile",
                            str(profile_path),
                            "--output-dir",
                            str(output_dir),
                            "--format",
                            "json",
                        ]
                    )

            payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertIn("checks", payload["data"])
        self.assertEqual(payload["data"]["checks"]["source_registry"]["status"], "pass")
        self.assertEqual(payload["meta"]["schema_version"], "agent_envelope_v1")

    def test_scan_format_json_uses_registry_and_writes_source_health(self):
        scan = load_module(self, "scan")

        class FakeClient:
            def __init__(self, session, api_id, api_hash, *, flood_sleep_threshold):
                pass

            async def connect(self):
                return None

            async def is_user_authorized(self):
                return True

            async def disconnect(self):
                return None

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "sources.json"
            output_path = root / "scan.jsonl"
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
                                "priority": "normal",
                                "expected_language": "en",
                                "scan_window_hours": 24,
                                "enabled": True,
                                "notes": "",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            parser = scan.build_parser()
            args = parser.parse_args(
                [
                    "--source-registry",
                    str(registry_path),
                    "--hours",
                    "6",
                    "--output",
                    str(output_path),
                    "--format",
                    "json",
                ]
            )
            stdout = io.StringIO()

            async def fake_resolve_entity(client, channel_name):
                return f"entity:{channel_name}"

            async def fake_read_channel(**kwargs):
                return scan.ChannelResult(
                    channel=kwargs["channel_name"],
                    messages=[
                        {
                            "id": 10,
                            "message_ref": {"channel": kwargs["channel_name"], "id": 10},
                            "channel": kwargs["channel_name"],
                            "date": "2026-05-08T10:00:00+00:00",
                            "text": "market signal",
                        }
                    ],
                    raw_count=3,
                    skipped_missing_date=0,
                    limit=kwargs["max_limit"],
                    incomplete=False,
                    ocr_count=0,
                    stderr="",
                )

            with patch.object(scan, "load_config", return_value=scan.ScannerConfig(1, "hash", "session")):
                with patch.object(scan, "StringSession", return_value="fake-session"):
                    with patch.object(scan, "TelegramClient", FakeClient):
                        with patch.object(scan, "resolve_entity", side_effect=fake_resolve_entity):
                            with patch.object(scan, "read_channel", side_effect=fake_read_channel):
                                with patch("sys.stdout", stdout):
                                    exit_code = asyncio.run(scan._run_scan(args))

            payload = json.loads(stdout.getvalue())
            meta = json.loads(output_path.with_suffix(".meta.json").read_text(encoding="utf-8"))

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["message_count"], 1)
        self.assertEqual(meta["source_health"][0]["source_id"], "telegram:cointelegraph")
        self.assertEqual(meta["source_health"][0]["raw_count"], 3)
        self.assertEqual(meta["source_health"][0]["kept_count"], 1)

    def test_daily_report_registry_json_returns_output_paths(self):
        daily_report = load_module(self, "daily_report")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry_path = root / "sources.json"
            profile_path = root / "profile.md"
            output_dir = root / "output"
            registry_path.write_text(
                json.dumps({"schema_version": "source_registry_v1", "sources": []}),
                encoding="utf-8",
            )
            profile_path.write_text("# Profile\n", encoding="utf-8")
            calls = []
            stdout = io.StringIO()

            def fake_run(cmd, **kwargs):
                calls.append(cmd)
                if "scan.py" in str(cmd[1]):
                    Path(cmd[cmd.index("--output") + 1]).write_text("{}", encoding="utf-8")
                if "report.py" in str(cmd[1]):
                    Path(cmd[cmd.index("--output") + 1]).write_text("# Report", encoding="utf-8")
                return SimpleNamespace(returncode=0)

            with patch.object(daily_report.subprocess, "run", side_effect=fake_run):
                with patch("sys.stdout", stdout):
                    exit_code = daily_report.main(
                        [
                            "--source-registry",
                            str(registry_path),
                            "--profile",
                            str(profile_path),
                            "--output-dir",
                            str(output_dir),
                            "--html",
                            "--format",
                            "json",
                        ]
                    )

            payload = json.loads(stdout.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertTrue(payload["ok"])
        self.assertIn("scan_path", payload["data"])
        self.assertIn("report_path", payload["data"])
        self.assertIn("--source-registry", calls[0])
        self.assertIn("--format", calls[0])
        self.assertIn("--format", calls[1])


if __name__ == "__main__":
    unittest.main()
