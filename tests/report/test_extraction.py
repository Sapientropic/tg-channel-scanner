import json
import re
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from .helpers import load_report_module, sample_messages


class ReportExtractionTests(unittest.TestCase):
    def test_custom_schema_prompt_keeps_source_refs_contract(self):
        report = load_report_module(self)
        profile = """# Custom watchlist

## Extraction Schema
mode: custom
top_level_key: items
dedup_fields: [project]
fields:
  - name: project
    required: true
  - name: rating
    values: [high, medium, low]

## Extraction Prompt
system_prompt: |
  Extract useful watchlist items.
"""
        profile_config = report.parse_profile_config(profile)

        system_prompt, _ = report.build_extraction_prompts(
            sample_messages(),
            profile,
            meta=None,
            max_messages=10,
            profile_config=profile_config,
        )

        self.assertIn('"source_message_refs": [{"channel": "channel name", "id": 123}]', system_prompt)
        self.assertIn('"source_message_ids": [123]', system_prompt)
        self.assertIn("source_message_refs with both channel and id", system_prompt)


    def test_parse_extraction_response_rejects_invalid_json_with_raw_response(self):
        report = load_report_module(self)

        with self.assertRaises(report.ReportError) as ctx:
            report.parse_extraction_response("not json")

        self.assertIn("valid JSON", str(ctx.exception))
        self.assertEqual(ctx.exception.raw_response, "not json")


    def test_deepseek_key_gets_matching_default_endpoint_and_model(self):
        report = load_report_module(self)

        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "sk-test"}, clear=True):
            base_url, model = report.resolve_llm_settings(None, report.DEFAULT_MODEL)

        self.assertEqual(base_url, report.DEFAULT_DEEPSEEK_BASE_URL)
        self.assertEqual(model, "deepseek-v4-flash")


    def test_minimax_token_plan_key_gets_china_endpoint_and_model(self):
        report = load_report_module(self)

        with patch.dict("os.environ", {"MINIMAX_TOKEN_PLAN_KEY": "sk-test"}, clear=True):
            base_url, model = report.resolve_llm_settings(None, report.DEFAULT_MODEL)

        self.assertEqual(report.DEFAULT_MINIMAX_TOKEN_PLAN_BASE_URL, "https://api.minimaxi.com/v1")
        self.assertEqual(base_url, report.DEFAULT_MINIMAX_TOKEN_PLAN_BASE_URL)
        self.assertEqual(model, "MiniMax-M2.7")


    def test_minimax_platform_key_keeps_platform_endpoint(self):
        report = load_report_module(self)

        with patch.dict("os.environ", {"MINIMAX_API_KEY": "sk-test"}, clear=True):
            base_url, model = report.resolve_llm_settings(None, report.DEFAULT_MODEL)

        self.assertEqual(base_url, report.DEFAULT_MINIMAX_BASE_URL)
        self.assertEqual(model, "MiniMax-M2.7")


    def test_minimax_region_cn_uses_china_endpoint(self):
        report = load_report_module(self)

        with patch.dict("os.environ", {"MINIMAX_API_KEY": "sk-test", "MINIMAX_REGION": "cn"}, clear=True):
            base_url, model = report.resolve_llm_settings(None, report.DEFAULT_MODEL)

        self.assertEqual(base_url, report.DEFAULT_MINIMAX_CN_BASE_URL)
        self.assertEqual(model, "MiniMax-M2.7")


    def test_explicit_deepseek_model_gets_deepseek_endpoint_even_when_minimax_key_exists(self):
        report = load_report_module(self)

        with patch.dict(
            "os.environ",
            {"DEEPSEEK_API_KEY": "sk-deepseek", "MINIMAX_TOKEN_PLAN_KEY": "sk-minimax"},
            clear=True,
        ):
            base_url, model = report.resolve_llm_settings(None, "deepseek-v4-flash")

        self.assertEqual(base_url, report.DEFAULT_DEEPSEEK_BASE_URL)
        self.assertEqual(model, "deepseek-v4-flash")


    def test_deepseek_key_wins_default_when_no_openai_key_and_minimax_also_exists(self):
        report = load_report_module(self)

        with patch.dict(
            "os.environ",
            {"DEEPSEEK_API_KEY": "sk-deepseek", "MINIMAX_TOKEN_PLAN_KEY": "sk-minimax"},
            clear=True,
        ):
            base_url, model = report.resolve_llm_settings(None, report.DEFAULT_MODEL)

        self.assertEqual(base_url, report.DEFAULT_DEEPSEEK_BASE_URL)
        self.assertEqual(model, "deepseek-v4-flash")


    def test_env_minimax_platform_key_beats_unrelated_local_deepseek_key(self):
        report = load_report_module(self)

        def fake_read_secret(target_name):
            if target_name == report.LOCAL_AI_SECRET_TARGETS["DEEPSEEK_API_KEY"]:
                return SimpleNamespace(secret="sk-local-deepseek")
            return None

        with patch.dict("os.environ", {"MINIMAX_API_KEY": "sk-minimax-env"}, clear=True):
            with patch.object(report.ai_secret.__globals__["local_credentials"], "read_secret", side_effect=fake_read_secret):
                base_url, model = report.resolve_llm_settings(None, report.DEFAULT_MODEL)

        self.assertEqual(base_url, report.DEFAULT_MINIMAX_BASE_URL)
        self.assertEqual(model, report.DEFAULT_MINIMAX_MODEL)


    def test_extraction_prompt_keeps_profile_in_cacheable_prefix(self):
        report = load_report_module(self)

        system_prompt, user_prompt = report.build_extraction_prompts(
            sample_messages(),
            "# Job Profile\nRemote TypeScript roles only.",
            meta={"scan_started_at": "2026-05-08T08:00:00Z"},
            max_messages=10,
        )

        self.assertIn("=== CANDIDATE PROFILE ===", system_prompt)
        self.assertIn("Remote TypeScript roles only.", system_prompt)
        self.assertNotIn("=== CANDIDATE PROFILE ===", user_prompt)
        self.assertLess(user_prompt.index("=== SCAN METADATA ==="), user_prompt.index("=== UNTRUSTED TELEGRAM MESSAGES"))


    def test_extraction_prompt_uses_cache_friendly_scan_metadata(self):
        report = load_report_module(self)

        _, user_prompt = report.build_extraction_prompts(
            [
                {
                    "channel": "jobs_a",
                    "id": 10,
                    "date": "2026-05-09T12:00:00Z",
                    "text": "Senior React remote role. Contact @hr.",
                    "origin_url": "https://t.me/original_jobs/10",
                    "origin_channel": "original_jobs",
                    "message_ref": {"channel": "jobs_a", "id": 10},
                    "sender_id": -100123,
                    "media_type": "MessageMediaPhoto",
                    "has_photo": True,
                    "monitor_prefilter": {"matched_keywords": ["react"]},
                }
            ],
            "# Job Profile\nRemote TypeScript roles only.",
            meta={
                "scan_date": "2026-05-09",
                "scan_started_at": "2026-05-09T12:25:31Z",
                "scan_completed_at": "2026-05-09T12:27:31Z",
                "scan_window": "Last 2 hours",
                "cutoff": "2026-05-09T10:25:31Z",
                "channel_count": 68,
                "total_messages_collected": 23,
                "failure_count": 0,
                "incomplete_count": 0,
                "ocr_enabled": False,
                "ocr_count": 0,
                "output_path": r"E:\workspace\output\runs\run-1\scan.jsonl",
                "errors_path": r"E:\workspace\output\runs\run-1\scan.errors.log",
                "source_registry_path": r"E:\workspace\output\runs\run-1\source-registry.filtered.json",
                "source_health": [
                    {
                        "channel": "jobs_a",
                        "raw_count": 9,
                        "kept_count": 7,
                        "oldest_message_at": "2026-05-09T11:00:00Z",
                    }
                ],
            },
            max_messages=10,
        )

        self.assertIn('"channel_count": 68', user_prompt)
        self.assertIn('"total_messages_collected": 23', user_prompt)
        self.assertIn('"scan_window": "Last 2 hours"', user_prompt)
        self.assertNotIn("source_health", user_prompt)
        self.assertNotIn("scan_started_at", user_prompt)
        self.assertNotIn("scan_completed_at", user_prompt)
        self.assertNotIn("cutoff", user_prompt)
        self.assertNotIn("output_path", user_prompt)
        self.assertNotIn("E:\\workspace", user_prompt)
        self.assertIn('"origin_url": "https://t.me/original_jobs/10"', user_prompt)
        self.assertNotIn("sender_id", user_prompt)
        self.assertNotIn("media_type", user_prompt)
        self.assertNotIn("monitor_prefilter", user_prompt)
        self.assertNotIn("message_ref", user_prompt)


    def test_deepseek_v4_extraction_disables_thinking_and_reports_cache_usage(self):
        report = load_report_module(self)
        captured: dict = {}

        class FakeUsage:
            def model_dump(self):
                return {
                    "prompt_tokens": 10,
                    "completion_tokens": 2,
                    "total_tokens": 12,
                    "prompt_cache_hit_tokens": 8,
                    "prompt_cache_miss_tokens": 2,
                }

        class FakeCompletions:
            def create(self, **kwargs):
                captured.update(kwargs)
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content='{"jobs": []}'))],
                    usage=FakeUsage(),
                )

        class FakeOpenAI:
            def __init__(self, *, api_key, base_url):
                captured["api_key"] = api_key
                captured["base_url"] = base_url
                self.chat = SimpleNamespace(completions=FakeCompletions())

        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "sk-test"}, clear=True):
            with patch.dict(sys.modules, {"openai": SimpleNamespace(OpenAI=FakeOpenAI)}):
                result = report.extract_jobs_with_metadata(
                    messages=sample_messages()[:1],
                    profile="Senior TypeScript roles",
                    meta=None,
                    base_url=report.DEFAULT_DEEPSEEK_BASE_URL,
                    model="deepseek-v4-flash",
                    max_messages=10,
                )

        self.assertEqual(result.items, [])
        self.assertEqual(captured["extra_body"], {"thinking": {"type": "disabled"}})
        self.assertEqual(captured["response_format"], {"type": "json_object"})
        self.assertEqual(captured["temperature"], 0)
        self.assertEqual(result.llm["provider"], "deepseek")
        self.assertEqual(result.llm["model"], "deepseek-v4-flash")
        self.assertEqual(result.llm["usage"]["prompt_cache_hit_tokens"], 8)
        self.assertEqual(result.llm["usage"]["prompt_cache_miss_tokens"], 2)
        self.assertIn("prompt_prefix_hash", result.llm)

    def test_extraction_can_split_messages_into_parallel_semantic_batches(self):
        report = load_report_module(self)
        captured_batches: list[list[int]] = []

        class FakeCompletions:
            def create(self, **kwargs):
                user_prompt = kwargs["messages"][1]["content"]
                message_ids = [int(match) for match in re.findall(r'"id":\s*(\d+)', user_prompt)]
                captured_batches.append(message_ids)
                first_id = message_ids[0]
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(
                                content=json.dumps(
                                    {
                                        "jobs": [
                                            {
                                                "source_message_refs": [{"channel": "jobs", "id": first_id}],
                                                "source_message_ids": [first_id],
                                                "company": f"Company {first_id}",
                                                "role": "Engineer",
                                                "rating": "high",
                                            }
                                        ]
                                    }
                                )
                            )
                        )
                    ],
                    usage={
                        "prompt_tokens": 10,
                        "completion_tokens": 2,
                        "total_tokens": 12,
                        "prompt_cache_hit_tokens": 8,
                        "prompt_cache_miss_tokens": 2,
                    },
                )

        class FakeOpenAI:
            def __init__(self, *, api_key, base_url):
                self.chat = SimpleNamespace(completions=FakeCompletions())

        with patch.dict("os.environ", {"DEEPSEEK_API_KEY": "sk-test"}, clear=True):
            with patch.dict(sys.modules, {"openai": SimpleNamespace(OpenAI=FakeOpenAI)}):
                result = report.extract_jobs_with_metadata(
                    messages=sample_messages(),
                    profile="Senior TypeScript roles",
                    meta=None,
                    base_url=report.DEFAULT_DEEPSEEK_BASE_URL,
                    model="deepseek-v4-flash",
                    max_messages=5,
                    max_tokens=6000,
                    semantic_batch_size=2,
                    semantic_concurrency=2,
                )

        self.assertEqual(len(captured_batches), 3)
        self.assertEqual(sorted(batch[0] for batch in captured_batches), [1, 3, 5])
        self.assertEqual(len(result.items), 3)
        self.assertEqual(result.llm["batch_count"], 3)
        self.assertEqual(result.llm["batch_size"], 2)
        self.assertEqual(result.llm["concurrency"], 2)
        self.assertEqual(result.llm["usage"]["prompt_tokens"], 30)
        self.assertEqual(result.llm["cache"]["hit_tokens"], 24)
        self.assertEqual(len(result.llm["batches"]), 3)

    def test_minimax_m27_extraction_uses_minimax_key_and_provider_safe_request_shape(self):
        report = load_report_module(self)
        captured: dict = {}

        class FakeCompletions:
            def create(self, **kwargs):
                captured.update(kwargs)
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content='{"jobs": []}'))],
                    usage={"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12},
                )

        class FakeOpenAI:
            def __init__(self, *, api_key, base_url):
                captured["api_key"] = api_key
                captured["base_url"] = base_url
                self.chat = SimpleNamespace(completions=FakeCompletions())

        with patch.dict(
            "os.environ",
            {
                "DEEPSEEK_API_KEY": "sk-deepseek",
                "MINIMAX_TOKEN_PLAN_KEY": "sk-minimax",
            },
            clear=True,
        ):
            with patch.dict(sys.modules, {"openai": SimpleNamespace(OpenAI=FakeOpenAI)}):
                base_url, model = report.resolve_llm_settings(None, "MiniMax-M2.7")
                result = report.extract_jobs_with_metadata(
                    messages=sample_messages()[:1],
                    profile="Senior TypeScript roles",
                    meta=None,
                    base_url=base_url,
                    model=model,
                    max_messages=10,
                    max_tokens=512,
                )

        self.assertEqual(result.items, [])
        self.assertEqual(captured["api_key"], "sk-minimax")
        self.assertEqual(captured["base_url"], report.DEFAULT_MINIMAX_CN_BASE_URL)
        self.assertEqual(captured["extra_body"], {"reasoning_split": True})
        self.assertGreater(captured["temperature"], 0)
        self.assertEqual(captured["max_completion_tokens"], 512)
        self.assertNotIn("max_tokens", captured)
        self.assertNotIn("response_format", captured)
        self.assertEqual(result.llm["provider"], "minimax")
        self.assertEqual(result.llm["thinking"], "split")


    def test_minimax_token_plan_key_takes_precedence_for_minimax_provider(self):
        report = load_report_module(self)

        with patch.dict(
            "os.environ",
            {
                "MINIMAX_API_KEY": "sk-general",
                "MINIMAX_TOKEN_PLAN_KEY": "sk-token-plan",
            },
            clear=True,
        ):
            key = report.api_key_for_provider("minimax")

        self.assertEqual(key, "sk-token-plan")


    def test_extraction_response_strips_minimax_thinking_block_before_json_parse(self):
        report = load_report_module(self)

        items = report.parse_extraction_response('<think>drafting</think>\n{"jobs": [{"rating": "high"}]}')

        self.assertEqual(items, [{"rating": "high"}])


    def test_openai_key_keeps_openai_defaults_when_both_keys_exist(self):
        report = load_report_module(self)

        with patch.dict(
            "os.environ",
            {"OPENAI_API_KEY": "sk-openai", "DEEPSEEK_API_KEY": "sk-deepseek"},
            clear=True,
        ):
            base_url, model = report.resolve_llm_settings(None, report.DEFAULT_MODEL)

        self.assertIsNone(base_url)
        self.assertEqual(model, report.DEFAULT_MODEL)



if __name__ == "__main__":
    unittest.main()
