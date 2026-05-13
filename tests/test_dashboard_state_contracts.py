import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import monitor_state


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "contracts" / "dashboard_state_v1.projection.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def pick_card(card: dict, index: int) -> dict:
    return {
        "schema_version": card.get("schema_version"),
        "card_id": f"card-{index + 1}",
        "profile_id": card.get("profile_id"),
        "title": card.get("title"),
        "rating": card.get("rating"),
        "decision_status": card.get("decision_status"),
        "source_refs": card.get("source_refs"),
        "item": {
            key: card.get("item", {}).get(key)
            for key in ("schema_version", "topic", "rating", "why", "decision_state", "source_message_refs")
            if key in card.get("item", {})
        },
        "status": card.get("status"),
        "opportunity_status": card.get("opportunity_status") or "open",
        "last_run_id": card.get("last_run_id"),
        "report_path": card.get("report_path"),
    }


def pick_dashboard_state(snapshot: dict) -> dict:
    profile_keys = (
        "schema_version",
        "profile_id",
        "display_name",
        "report_display_name",
        "display_path",
        "enabled",
        "alert_schedule_mode",
        "source_topics",
        "scan_window_hours",
        "semantic_max_messages",
        "delivery_target_count",
    )
    run_keys = (
        "run_id",
        "profile_id",
        "display_name",
        "status",
        "review_card_count",
        "alert_count",
        "report_artifact",
    )
    quality_keys = (
        "prefilter",
        "semantic_stage",
        "llm_provider",
        "cache_hit_rate",
        "latency_ms",
        "completion_tokens",
        "diagnostic_count",
        "diagnostic_warning_count",
        "diagnostic_failure_count",
        "top_diagnostic_code",
    )
    target_keys = (
        "schema_version",
        "target_id",
        "type",
        "enabled",
        "config",
        "display_name",
        "status_label",
        "detail",
    )
    feedback = snapshot["feedback_summary"]
    setup = snapshot["setup_status"]
    opportunity = snapshot["opportunity_summary"]
    insights = [
        {
            "channel": item.get("channel"),
            "display_name": item.get("display_name"),
            "kind": item.get("kind"),
            "label": item.get("label"),
            "reason": item.get("reason"),
            "next_action": {"label": item.get("next_action", {}).get("label")},
        }
        for item in snapshot["source_insights"]
        if item.get("channel") in {"jobs_good", "jobs_noise"}
    ]
    return {
        "schema_version": snapshot.get("schema_version"),
        "profiles": [{key: profile.get(key) for key in profile_keys} for profile in snapshot["profiles"]],
        "runs": [
            {
                **{key: run.get(key) for key in run_keys},
                "quality": {key: run.get("quality", {}).get(key) for key in quality_keys},
            }
            for run in snapshot["runs"]
        ],
        "inbox": [
            pick_card(card, index)
            for index, card in enumerate(sorted(snapshot["inbox"], key=lambda item: item["title"]))
        ],
        "delivery_targets": [{key: target.get(key) for key in target_keys} for target in snapshot["delivery_targets"]],
        "feedback_summary": {
            "schema_version": feedback.get("schema_version"),
            "exportable_count": feedback.get("exportable_count"),
            "by_action": feedback.get("by_action"),
            "by_rating": feedback.get("by_rating"),
            "by_decision_status": feedback.get("by_decision_status"),
            "next_action": {
                "label": feedback.get("next_action", {}).get("label"),
                "detail": feedback.get("next_action", {}).get("detail"),
            },
        },
        "setup_status": {
            "stage": setup.get("stage"),
            "next_step": setup.get("next_step"),
            "has_profiles": setup.get("has_profiles"),
            "has_runs": setup.get("has_runs"),
            "delivery_configured": setup.get("delivery_configured"),
            "delivery_enabled": setup.get("delivery_enabled"),
            "checks": [
                {"check_id": item.get("check_id"), "status": item.get("status")}
                for item in setup.get("checks", [])
                if item.get("check_id") in {"profiles", "first_run", "delivery"}
            ],
        },
        "opportunity_summary": {
            "schema_version": opportunity.get("schema_version"),
            "status": opportunity.get("status"),
            "run_id": opportunity.get("run_id"),
            "profile_id": opportunity.get("profile_id"),
            "display_name": opportunity.get("display_name"),
            "scanned_count": opportunity.get("scanned_count"),
            "matched_count": opportunity.get("matched_count"),
            "review_card_count": opportunity.get("review_card_count"),
            "alert_count": opportunity.get("alert_count"),
            "high_actionable_count": opportunity.get("high_actionable_count"),
            "all_clear": opportunity.get("all_clear"),
            "top_items": sorted(
                [
                    {
                        "title": item.get("title"),
                        "rating": item.get("rating"),
                        "decision_status": item.get("decision_status"),
                    }
                    for item in opportunity.get("top_items", [])
                ],
                key=lambda item: item["title"],
            ),
            "decision_counts": opportunity.get("decision_counts"),
            "diagnostics": opportunity.get("diagnostics"),
            "next_action": {
                "label": opportunity.get("next_action", {}).get("label"),
                "detail": opportunity.get("next_action", {}).get("detail"),
            },
        },
        "source_insights": sorted(insights, key=lambda item: item["channel"]),
        "validation_summary": {
            key: snapshot["validation_summary"].get(key)
            for key in (
                "schema_version",
                "card_count",
                "action_count",
                "triage_rate",
                "keep_rate",
                "false_positive_rate",
            )
        },
    }


def build_dashboard_snapshot(root: Path) -> dict:
    profile_path = root / "profiles" / "templates" / "jobs.md"
    profile_path.parent.mkdir(parents=True)
    profile_path.write_text("# Job Scan\n\n## Search Rules\n- TypeScript roles.\n", encoding="utf-8")
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    monitor_state.init_db(conn)
    monitor_state.upsert_profile(
        conn,
        {
            "id": "jobs-fast",
            "path": "profiles/templates/jobs.md",
            "enabled": True,
            "source_topics": ["jobs"],
            "alert_schedule_mode": "work_hours",
            "scan_window_hours": 2,
            "semantic_max_messages": 20,
            "delivery_targets": ["telegram-bot-default"],
        },
    )
    monitor_state.upsert_delivery_target(
        conn,
        {
            "id": "telegram-bot-default",
            "type": "telegram_bot",
            "enabled": True,
            "chat_id": "123456",
            "token": "SECRET_DASHBOARD_TOKEN_SHOULD_NOT_SURFACE",
            "bot_token": "SECRET_DASHBOARD_TOKEN_SHOULD_NOT_SURFACE",
        },
    )
    monitor_state.record_run(
        conn,
        {
            "schema_version": "run_manifest_v1",
            "run_id": "run-dashboard-contract",
            "profile_id": "jobs-fast",
            "profile_path": "profiles/templates/jobs.md",
            "status": "complete",
            "started_at": "2026-05-13T00:00:00Z",
            "completed_at": "2026-05-13T00:01:00Z",
            "prefilter": {
                "raw_message_count": 12,
                "matched_count": 3,
                "semantic_stage": "report_ran",
            },
            "llm": {
                "provider": "deepseek",
                "latency_ms": 640,
                "cache": {"hit_rate": 0.91},
                "usage": {"completion_tokens": 88},
            },
            "diagnostics": [
                {
                    "code": "scan_incomplete",
                    "severity": "warning",
                    "message": "One source may be incomplete.",
                    "next_step": "Rerun with a narrower scan window.",
                }
            ],
            "review_card_count": 4,
            "alert_count": 1,
            "artifacts": [
                {
                    "artifact_id": "report:html",
                    "type": "report_html",
                    "path": "output/runs/run-dashboard-contract/report.html",
                    "category": "reports",
                    "format": "HTML",
                    "display_name": "Job Scan Report",
                    "display_path": "Reports/report.html",
                }
            ],
        },
    )
    cards = monitor_state.upsert_review_cards(
        conn,
        profile_id="jobs-fast",
        run_id="run-dashboard-contract",
        report_path="output/runs/run-dashboard-contract/report.md",
        items=[
            {
                "topic": "Great TypeScript role",
                "rating": "high",
                "why": "Matches the target profile.",
                "decision_state": {"status": "new", "semantic_cluster": "contract-high-1"},
                "source_message_refs": [{"channel": "jobs_good", "id": 1}],
                "raw_text": "RAW_DASHBOARD_CONTRACT_SHOULD_NOT_SURFACE",
                "token": "SECRET_DASHBOARD_TOKEN_SHOULD_NOT_SURFACE",
                "path": "C:/Users/Administrator/private/scan.jsonl",
                "argv": ["--private-argv"],
            },
            {
                "topic": "Another TypeScript platform role",
                "rating": "high",
                "why": "Second high signal from the same source.",
                "decision_state": {"status": "new", "semantic_cluster": "contract-high-2"},
                "source_message_refs": [{"channel": "jobs_good", "id": 2}],
            },
            {
                "topic": "Generic chatter",
                "rating": "low",
                "why": "Not a qualified opportunity.",
                "decision_state": {"status": "new", "semantic_cluster": "contract-low-1"},
                "source_message_refs": [{"channel": "jobs_noise", "id": 3}],
            },
            {
                "topic": "Misleading repost",
                "rating": "low",
                "why": "False-positive repost.",
                "decision_state": {"status": "new", "semantic_cluster": "contract-low-2"},
                "source_message_refs": [{"channel": "jobs_noise", "id": 4}],
            },
        ],
    )
    monitor_state.set_card_action(conn, card_id=cards[2]["card_id"], action="false_positive")
    monitor_state.set_card_action(conn, card_id=cards[3]["card_id"], action="false_positive")
    return monitor_state.dashboard_snapshot(conn)


class DashboardStateContractTests(unittest.TestCase):
    def test_dashboard_snapshot_matches_shared_projection_fixture(self):
        fixture = load_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(monitor_state, "PROJECT_ROOT", root):
                snapshot = build_dashboard_snapshot(root)

        normalized = pick_dashboard_state(snapshot)

        self.assertEqual(normalized, fixture["dashboard_state"])
        surfaced = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
        for denied in fixture["denied_strings"]:
            with self.subTest(denied=denied):
                self.assertNotIn(denied, surfaced)


if __name__ == "__main__":
    unittest.main()
