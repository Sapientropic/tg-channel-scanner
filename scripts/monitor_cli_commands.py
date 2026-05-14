"""Auxiliary monitor CLI commands outside the profile run pipeline."""

from __future__ import annotations

import argparse
import json

from scripts import agent_cli, delivery, monitor_state
from scripts.monitor_config import PROFILE_RUN_CONFIG_SCHEMA_VERSION, relative_to_root, root_path


def test_telegram_bot(args: argparse.Namespace) -> int:
    chat_id = args.chat_id or ""
    if not chat_id:
        agent_cli.emit_error(
            args,
            code="telegram_bot_chat_id_missing",
            message="Telegram bot chat_id is required for delivery test.",
            retryable=False,
            next_step="Pass --chat-id or add a chat_id to .tgcs/profiles.toml.",
        )
        return agent_cli.EXIT_VALIDATION
    attempt = delivery.send_telegram_bot_message(
        target_id=args.target_id,
        chat_id=chat_id,
        text="T-Sense delivery test.",
        mode=args.delivery_mode,
    )
    if agent_cli.is_json_format(args):
        agent_cli.print_json(agent_cli.envelope_success({"attempt": attempt.to_dict()}))
    else:
        print(f"Telegram bot delivery test: {attempt.status}")
    return agent_cli.EXIT_SUCCESS if attempt.ok else agent_cli.EXIT_RUNTIME


def write_default_config(args: argparse.Namespace) -> int:
    config_path = root_path(args.config)
    if config_path.exists() and not args.force:
        if not agent_cli.is_json_format(args):
            print(f"Profile run config already exists: {config_path}")
        return agent_cli.EXIT_SUCCESS
    config_path.parent.mkdir(parents=True, exist_ok=True)
    text = """schema_version = "profile_run_config_v1"

[defaults]
output_dir = "output"
state_dir = ".tgcs/state"
database = ".tgcs/tgcs.db"
dashboard_url = "http://127.0.0.1:8765"

[[profiles]]
id = "market-news"
path = "profiles/templates/market-news.md"
enabled = true
timezone = "Asia/Shanghai"
work_interval_minutes = 120
off_hours_interval_minutes = 360
scan_window_hours = 24
source_registry = ".tgcs/sources.json"
channel_list = "channel_lists/example.txt"
source_topics = ["market-news"]
alert_rule = "high_new_or_changed"
alert_schedule_mode = "work_hours"
delivery_targets = ["telegram-bot-default"]
dashboard_visible = true

[[profiles]]
id = "jobs-fast"
path = "profiles/templates/jobs.md"
enabled = true
timezone = "Asia/Shanghai"
work_start = "09:00"
work_end = "23:00"
work_interval_minutes = 15
off_hours_interval_minutes = 60
scan_window_hours = 2
source_registry = ".tgcs/sources.json"
channel_list = "channel_lists/example.txt"
source_topics = ["jobs"]
alert_rule = "high_new_or_changed"
alert_max_age_minutes = 60
alert_schedule_mode = "work_hours"
delivery_targets = ["telegram-bot-default"]
dashboard_visible = true
prefilter_enabled = true
# Keep high-frequency alert batches bounded; use a separate backfill/audit lane
# if you need exhaustive semantic extraction over a larger catch-up window.
scan_concurrency = 3
scan_delay_seconds = 0.2
semantic_max_messages = 40
semantic_max_tokens = 6000
semantic_batch_size = 20
semantic_concurrency = 2
prefilter_keywords = [
  "hiring",
  "we're hiring",
  "is hiring",
  "job opening",
  "open role",
  "remote",
  "apply",
  "frontend",
  "backend",
  "fullstack",
  "react",
  "typescript",
  "engineer",
  "developer",
  "freelance",
  "contract",
  "contractor",
  "gig",
  "bounty",
  "paid project",
  "mini app",
  "mini apps",
  "telegram mini app",
  "ton",
  "usdt",
  "budget",
  "招聘",
  "招人",
  "岗位",
  "职位",
  "远程",
  "外包",
  "兼职",
  "私活",
  "项目",
  "预算",
]

[[delivery]]
id = "telegram-bot-default"
type = "telegram_bot"
enabled = false
chat_id = ""
"""
    config_path.write_text(text, encoding="utf-8")
    data = {"schema_version": PROFILE_RUN_CONFIG_SCHEMA_VERSION, "config_path": relative_to_root(config_path)}
    if agent_cli.is_json_format(args):
        agent_cli.print_json(agent_cli.envelope_success(data))
    else:
        print(f"Profile run config written: {config_path}")
    return agent_cli.EXIT_SUCCESS


def export_feedback(args: argparse.Namespace) -> int:
    db_path = root_path(args.db)
    output_path = root_path(args.output)
    conn = monitor_state.connect(db_path)
    try:
        entries = monitor_state.export_feedback_entries(conn)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(entry, ensure_ascii=False) for entry in entries]
        output_path.write_text(("\n".join(lines) + "\n") if lines else "", encoding="utf-8")
        exported_at = monitor_state.utc_now()
        monitor_state.record_feedback_export(
            conn,
            output_path=relative_to_root(output_path),
            feedback_count=len(entries),
            exported_at=exported_at,
        )
    finally:
        conn.close()

    data = {
        "schema_version": "feedback_export_result_v1",
        "feedback_count": len(entries),
        "output_path": relative_to_root(output_path),
        "changed_since_last_export": False,
        "exported_at": exported_at,
    }
    if agent_cli.is_json_format(args):
        agent_cli.print_json(agent_cli.envelope_success(data))
    else:
        print(f"Feedback exported: {output_path} ({len(entries)} rows)")
    return agent_cli.EXIT_SUCCESS
