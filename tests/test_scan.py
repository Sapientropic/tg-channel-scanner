import asyncio
import getpass
import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from scripts import scan
from telethon.errors import FloodWaitError, SessionPasswordNeededError


def _make_mock_message(msg_id: int, date_str: str, text: str = ""):
    msg = MagicMock()
    msg.id = msg_id
    msg.text = text
    msg.sender_id = None
    msg.media = None
    msg.reply_to = None
    if date_str:
        text_date = date_str
        if text_date.endswith("Z"):
            text_date = f"{text_date[:-1]}+00:00"
        msg.date = datetime.fromisoformat(text_date)
    else:
        msg.date = None
    return msg


class AsyncIteratorMock:
    """Wrap a list as an async iterator for mocking iter_dialogs()."""

    def __init__(self, items):
        self._items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration


class ScanTests(unittest.TestCase):
    def test_precise_time_filter_keeps_only_messages_at_or_after_cutoff(self):
        cutoff = datetime(2026, 5, 6, 7, 30, tzinfo=timezone.utc)
        rows = [
            {"id": 1, "date": "2026-05-06T07:29:59+00:00", "text": "old"},
            {"id": 2, "date": "2026-05-06T07:30:00+00:00", "text": "boundary"},
            {"id": 3, "date": "2026-05-06T08:00:00Z", "text": "new"},
        ]

        kept, skipped = scan.filter_messages(rows, cutoff)

        self.assertEqual([row["id"] for row in kept], [2, 3])
        self.assertEqual(skipped, 0)

    def test_channel_read_doubles_limit_until_result_is_not_saturated(self):
        cutoff = datetime(2026, 5, 6, 7, 30, tzinfo=timezone.utc)
        batch1 = [
            _make_mock_message(3, "2026-05-06T08:00:00+00:00"),
            _make_mock_message(2, "2026-05-06T07:30:00+00:00"),
        ]
        batch2 = [
            _make_mock_message(3, "2026-05-06T08:00:00+00:00"),
            _make_mock_message(2, "2026-05-06T07:30:00+00:00"),
            _make_mock_message(1, "2026-05-06T06:00:00+00:00"),
        ]

        client = MagicMock()
        client.get_messages = AsyncMock(side_effect=[batch1, batch2])

        result = asyncio.run(
            scan.read_channel(client, "entity", "jobs", cutoff, 2, 4)
        )

        self.assertFalse(result.incomplete)
        self.assertEqual(result.raw_count, 3)
        self.assertEqual([m["id"] for m in result.messages], [3, 2])

    def test_channel_read_reports_incomplete_when_max_limit_is_still_saturated(self):
        cutoff = datetime(2026, 5, 6, 7, 30, tzinfo=timezone.utc)
        msgs = [
            _make_mock_message(4, "2026-05-06T09:00:00+00:00"),
            _make_mock_message(3, "2026-05-06T08:00:00+00:00"),
            _make_mock_message(2, "2026-05-06T07:30:00+00:00"),
            _make_mock_message(1, "2026-05-06T06:00:00+00:00"),
        ]

        client = MagicMock()
        client.get_messages = AsyncMock(side_effect=[msgs[:2], msgs])

        result = asyncio.run(
            scan.read_channel(client, "entity", "jobs", cutoff, 2, 4)
        )

        self.assertTrue(result.incomplete)
        self.assertEqual(result.raw_count, 4)

    def test_load_channel_list_trims_whitespace_and_ignores_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "channels.txt"
            path.write_text(
                "\n# comment\n  jobs_a  \n\njobs_b\n", encoding="utf-8"
            )

            self.assertEqual(
                scan.load_channel_list(path), ["jobs_a", "jobs_b"]
            )

    def test_resolve_entity_by_username(self):
        entity = MagicMock()
        client = MagicMock()
        client.get_entity = AsyncMock(return_value=entity)

        result = asyncio.run(scan.resolve_entity(client, "remote_italic"))
        self.assertEqual(result, entity)

    def test_resolve_entity_by_display_name(self):
        entity = MagicMock()
        entity.username = "remote_italic"

        dialog = MagicMock()
        dialog.name = "Remote Italic"
        dialog.entity = entity

        client = MagicMock()
        client.get_entity = AsyncMock(side_effect=Exception("not found"))
        client.iter_dialogs = MagicMock(return_value=AsyncIteratorMock([dialog]))

        result = asyncio.run(scan.resolve_entity(client, "Remote Italic"))
        self.assertEqual(result, entity)

    def test_resolve_entity_raises_on_unknown(self):
        client = MagicMock()
        client.get_entity = AsyncMock(side_effect=Exception("not found"))
        client.iter_dialogs = MagicMock(return_value=AsyncIteratorMock([]))

        with self.assertRaises(scan.ScanError):
            asyncio.run(scan.resolve_entity(client, "nonexistent_channel"))

    def test_message_to_dict_extracts_media_fields(self):
        msg = MagicMock()
        msg.id = 42
        msg.date = datetime(2026, 5, 6, 8, 0, tzinfo=timezone.utc)
        msg.text = "hello"
        msg.sender_id = 123
        msg.reply_to = None
        msg.voice = False
        msg.video = False

        # Use a real MessageMediaPhoto instance for isinstance check
        from telethon.tl.types import MessageMediaPhoto as RealPhoto

        msg.media = RealPhoto(photo=MagicMock(), spoiler=False)

        result = scan.message_to_dict(msg, "test_channel")
        self.assertTrue(result["has_photo"])
        self.assertEqual(result["media_type"], "MessageMediaPhoto")
        self.assertEqual(result["media_group"], "photo")
        self.assertNotIn("media_path", result)

    def test_ocr_default_is_disabled_even_when_openai_key_exists(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True):
            parser = scan.build_parser()
            args = parser.parse_args(["channel_lists/example.txt"])

            self.assertIsNone(scan._make_ocr_config(args))

    def test_ocr_openai_provider_uses_openai_default_base_url(self):
        created = []

        class FakeOpenAI:
            def __init__(self, *, base_url, api_key):
                created.append((base_url, api_key))

        fake_openai = SimpleNamespace(OpenAI=FakeOpenAI)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True):
            with patch.object(scan, "openai", fake_openai):
                parser = scan.build_parser()
                args = parser.parse_args(
                    [
                        "channel_lists/example.txt",
                        "--ocr",
                        "--ocr-provider",
                        "openai",
                    ]
                )

                cfg = scan._make_ocr_config(args)

        self.assertIsNotNone(cfg)
        self.assertEqual(created[0], ("https://api.openai.com/v1", "sk-test"))

    def test_ocr_custom_provider_uses_explicit_base_url(self):
        created = []

        class FakeOpenAI:
            def __init__(self, *, base_url, api_key):
                created.append((base_url, api_key))

        fake_openai = SimpleNamespace(OpenAI=FakeOpenAI)
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}, clear=True):
            with patch.object(scan, "openai", fake_openai):
                parser = scan.build_parser()
                args = parser.parse_args(
                    [
                        "channel_lists/example.txt",
                        "--ocr",
                        "--ocr-provider",
                        "custom",
                        "--ocr-base-url",
                        "http://localhost:11434/v1",
                    ]
                )

                cfg = scan._make_ocr_config(args)

        self.assertIsNotNone(cfg)
        self.assertEqual(created[0], ("http://localhost:11434/v1", "sk-test"))

    def test_invalid_scan_initial_limit_env_reports_parser_error(self):
        with patch.dict(os.environ, {"SCAN_INITIAL_LIMIT": "abc"}, clear=True):
            parser = scan.build_parser()
            stderr = io.StringIO()
            with patch("sys.stderr", stderr):
                with self.assertRaises(SystemExit):
                    parser.parse_args(["channel_lists/example.txt"])

        self.assertIn("SCAN_INITIAL_LIMIT", stderr.getvalue())

    def test_invalid_scan_env_reports_parser_error_before_help(self):
        with patch.dict(os.environ, {"SCAN_DELAY": "nope"}, clear=True):
            parser = scan.build_parser()
            stderr = io.StringIO()
            with patch("sys.stderr", stderr):
                with self.assertRaises(SystemExit):
                    parser.parse_args(["--help"])

        self.assertIn("SCAN_DELAY", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    def test_fetch_with_retry_sleeps_full_flood_wait_when_under_threshold(self):
        client = MagicMock()
        client.get_messages = AsyncMock(
            side_effect=[
                FloodWaitError(request=None, capture=2),
                [_make_mock_message(1, "2026-05-06T08:00:00+00:00")],
            ]
        )

        with patch.object(scan.asyncio, "sleep", AsyncMock()) as sleep:
            result = asyncio.run(
                scan._fetch_with_retry(
                    client,
                    "entity",
                    "jobs",
                    limit=10,
                    max_flood_wait_seconds=10,
                )
            )

        self.assertEqual(len(result), 1)
        sleep.assert_awaited_once_with(2)

    def test_fetch_with_retry_raises_when_flood_wait_exceeds_threshold(self):
        client = MagicMock()
        client.get_messages = AsyncMock(
            side_effect=FloodWaitError(request=None, capture=120)
        )

        with patch.object(scan.asyncio, "sleep", AsyncMock()) as sleep:
            with self.assertRaises(scan.ScanError) as ctx:
                asyncio.run(
                    scan._fetch_with_retry(
                        client,
                        "entity",
                        "jobs",
                        limit=10,
                        max_flood_wait_seconds=60,
                    )
                )

        self.assertIn("exceeds configured maximum", str(ctx.exception))
        sleep.assert_not_called()

    def test_interactive_login_handles_two_factor_password(self):
        client = MagicMock()
        client.send_code_request = AsyncMock()
        client.sign_in = AsyncMock(
            side_effect=[
                SessionPasswordNeededError(request=None),
                None,
            ]
        )
        client.session = "session"

        with tempfile.TemporaryDirectory() as tmp:
            session_path = Path(tmp) / "session"
            with patch.object(scan, "SESSION_PATH", session_path):
                with patch("builtins.input", side_effect=["+15550000000", "12345"]):
                    with patch.object(getpass, "getpass", return_value="2fa-secret"):
                        with patch.object(
                            scan.StringSession, "save", return_value="saved-session"
                        ):
                            asyncio.run(scan.interactive_login(client))
            saved_session = session_path.read_text(encoding="utf-8")

        self.assertEqual(client.sign_in.await_args_list[0].args, ("+15550000000", "12345"))
        self.assertEqual(client.sign_in.await_args_list[1].kwargs, {"password": "2fa-secret"})
        self.assertEqual(saved_session, "saved-session")

    def test_scan_metadata_sidecar_path_and_fields_are_stable(self):
        started = datetime(2026, 5, 6, 8, 0, tzinfo=timezone.utc)
        completed = datetime(2026, 5, 6, 8, 1, tzinfo=timezone.utc)
        cutoff = datetime(2026, 5, 5, 8, 0, tzinfo=timezone.utc)
        output_path = Path("output") / "scan_20260506_080000.jsonl"
        errors_path = Path("output") / "scan_20260506_080000.errors.log"

        try:
            meta_path = scan.meta_path_for_output(output_path)
            metadata = scan.build_scan_metadata(
                started_at=started,
                completed_at=completed,
                cutoff=cutoff,
                channel_list_path=Path("channel_lists/example.txt"),
                channels=["react_jobs", "frontend_jobs"],
                output_path=output_path,
                errors_path=errors_path,
                total_written=7,
                failed_channels=["frontend_jobs"],
                incomplete_channels=["react_jobs"],
                total_ocr=2,
                ocr_enabled=True,
                hours=24,
            )
        except AttributeError as exc:
            self.fail(f"scan metadata helpers should exist: {exc}")

        self.assertEqual(meta_path, Path("output") / "scan_20260506_080000.meta.json")
        self.assertEqual(metadata["scan_date"], "2026-05-06")
        self.assertEqual(metadata["scan_window"], "Last 24 hours")
        self.assertEqual(metadata["channel_count"], 2)
        self.assertEqual(metadata["channels"], ["react_jobs", "frontend_jobs"])
        self.assertEqual(metadata["total_messages_collected"], 7)
        self.assertEqual(metadata["failed_channels"], ["frontend_jobs"])
        self.assertEqual(metadata["incomplete_channels"], ["react_jobs"])
        self.assertEqual(metadata["ocr_count"], 2)
        self.assertTrue(metadata["ocr_enabled"])
        self.assertEqual(metadata["output_path"], str(output_path))
        self.assertEqual(metadata["errors_path"], str(errors_path))

    def test_write_scan_metadata_writes_json_sidecar(self):
        metadata = {"scan_date": "2026-05-06", "channel_count": 2}

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "scan_20260506_080000.meta.json"
            try:
                scan.write_scan_metadata(path, metadata)
            except AttributeError as exc:
                self.fail(f"write_scan_metadata should exist: {exc}")
            written = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(written, metadata)


if __name__ == "__main__":
    unittest.main()
