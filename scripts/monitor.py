"""v0.5-alpha profile monitor runner.

The monitor is a thin orchestration layer over the existing scan/report
contract.  It adds repeatable run manifests, SQLite-backed review/alert state,
and delivery hooks without changing the stable v0.4 report CLI.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scripts import agent_cli, delivery, monitor_state
except ModuleNotFoundError:
    _PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    from scripts import agent_cli, delivery, monitor_state


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROFILE_RUN_CONFIG_SCHEMA_VERSION = "profile_run_config_v1"
RUN_MANIFEST_SCHEMA_VERSION = "run_manifest_v1"
DEFAULT_PROFILE_ID = "market-news"
DEFAULT_DASHBOARD_URL = "http://127.0.0.1:8765"


@dataclass
class MonitorConfig:
    path: Path
    profiles: dict[str, dict[str, Any]]
    delivery_targets: dict[str, dict[str, Any]]
    defaults: dict[str, Any]


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_id() -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"run_{stamp}_{uuid.uuid4().hex[:8]}"


def root_path(value: str | Path, root: Path = PROJECT_ROOT) -> Path:
    path = Path(value)
    return path if path.is_absolute() else root / path


def relative_to_root(path: str | Path | None, root: Path = PROJECT_ROOT) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    try:
        return str(candidate.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(candidate)


def file_hash(path: Path | None) -> str | None:
    if path is None or not path.exists() or not path.is_file():
        return None
    return monitor_state.sha256_text(path.read_text(encoding="utf-8"))


def artifact(path: Path, artifact_type: str) -> dict[str, Any]:
    return {
        "artifact_id": f"{artifact_type}:{path.name}",
        "type": artifact_type,
        "path": relative_to_root(path),
        "sha256": file_hash(path),
    }


def default_config(config_path: Path) -> MonitorConfig:
    defaults = {
        "output_dir": "output",
        "state_dir": ".tgcs/state",
        "database": ".tgcs/tgcs.db",
        "dashboard_url": DEFAULT_DASHBOARD_URL,
    }
    profile = {
        "id": DEFAULT_PROFILE_ID,
        "path": "profiles/templates/market-news.md",
        "enabled": True,
        "timezone": "Asia/Shanghai",
        "work_interval_minutes": 120,
        "off_hours_interval_minutes": 360,
        "source_registry": ".tgcs/sources.json",
        "channel_list": "channel_lists/example.txt",
        "source_topics": ["market-news"],
        "alert_rule": "high_new_or_changed",
        "delivery_targets": ["telegram-bot-default"],
        "dashboard_visible": True,
    }
    target = {
        "id": "telegram-bot-default",
        "type": "telegram_bot",
        "enabled": False,
        "chat_id": "",
    }
    return MonitorConfig(
        path=config_path,
        profiles={profile["id"]: profile},
        delivery_targets={target["id"]: target},
        defaults=defaults,
    )


def load_config(config_path: Path, root: Path = PROJECT_ROOT) -> MonitorConfig:
    if not config_path.exists():
        return default_config(config_path)
    try:
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Profile run config is not valid TOML: {exc}") from exc
    if payload.get("schema_version") not in {None, PROFILE_RUN_CONFIG_SCHEMA_VERSION}:
        raise ValueError(f"schema_version must be {PROFILE_RUN_CONFIG_SCHEMA_VERSION}")
    defaults = payload.get("defaults") if isinstance(payload.get("defaults"), dict) else {}
    base = default_config(config_path)
    merged_defaults = {**base.defaults, **defaults}
    raw_profiles = payload.get("profiles")
    if not isinstance(raw_profiles, list) or not raw_profiles:
        raw_profiles = list(base.profiles.values())
    profiles: dict[str, dict[str, Any]] = {}
    for raw in raw_profiles:
        if not isinstance(raw, dict) or not raw.get("id"):
            continue
        item = dict(raw)
        item.setdefault("enabled", True)
        item.setdefault("alert_rule", "high_new_or_changed")
        item.setdefault("dashboard_visible", True)
        item.setdefault("source_registry", merged_defaults.get("source_registry", ".tgcs/sources.json"))
        item.setdefault("channel_list", merged_defaults.get("channel_list", "channel_lists/example.txt"))
        item.setdefault("delivery_targets", ["telegram-bot-default"])
        profiles[str(item["id"])] = item
    raw_targets = payload.get("delivery")
    if not isinstance(raw_targets, list) or not raw_targets:
        raw_targets = list(base.delivery_targets.values())
    targets: dict[str, dict[str, Any]] = {}
    for raw in raw_targets:
        if not isinstance(raw, dict) or not raw.get("id"):
            continue
        item = dict(raw)
        item.setdefault("type", "telegram_bot")
        item.setdefault("enabled", False)
        targets[str(item["id"])] = item
    return MonitorConfig(
        path=root_path(config_path, root),
        profiles=profiles,
        delivery_targets=targets,
        defaults=merged_defaults,
    )


def profile_path(profile: dict[str, Any], root: Path = PROJECT_ROOT) -> Path:
    return root_path(profile.get("path") or f"profiles/templates/{profile['id']}.md", root)


def source_input_args(profile: dict[str, Any], run_dir: Path, root: Path = PROJECT_ROOT) -> list[str]:
    registry = root_path(profile.get("source_registry") or ".tgcs/sources.json", root)
    if registry.exists():
        filtered = filter_source_registry(registry, run_dir, profile)
        return ["--source-registry", str(filtered)]
    channel_list = root_path(profile.get("channel_list") or "channel_lists/example.txt", root)
    return [str(channel_list)] if channel_list.exists() else []


def filter_source_registry(registry: Path, run_dir: Path, profile: dict[str, Any]) -> Path:
    topics = {str(item) for item in profile.get("source_topics") or profile.get("topics") or []}
    source_ids = {str(item) for item in profile.get("source_ids") or []}
    if not topics and not source_ids:
        return registry
    payload = json.loads(registry.read_text(encoding="utf-8"))
    sources = payload.get("sources") if isinstance(payload.get("sources"), list) else []
    filtered = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        source_topics = {str(item) for item in source.get("topics") or []}
        if source_ids and source.get("source_id") in source_ids:
            filtered.append(source)
        elif topics and source_topics.intersection(topics):
            filtered.append(source)
    filtered_payload = dict(payload)
    filtered_payload["sources"] = filtered
    filtered_path = run_dir / "source-registry.filtered.json"
    filtered_path.write_text(json.dumps(filtered_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return filtered_path


def parse_agent_stdout(completed: subprocess.CompletedProcess[str]) -> dict[str, Any] | None:
    if not completed.stdout:
        return None
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def run_json_command(cmd: list[str | Path]) -> tuple[int, dict[str, Any] | None, str]:
    completed = subprocess.run(
        [str(part) for part in cmd],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.returncode, parse_agent_stdout(completed), completed.stderr or ""


def report_command_for_scan_input(
    *,
    scan_input: Path,
    profile_file: Path,
    run_dir: Path,
    state_dir: Path,
    source_registry: Path | None,
    items_json: str | None,
) -> list[str | Path]:
    report_output = run_dir / "report.md"
    html_output = run_dir / "report.html"
    cmd: list[str | Path] = [
        sys.executable,
        PROJECT_ROOT / "scripts" / "report.py",
        "--input",
        scan_input,
        "--profile",
        profile_file,
        "--output",
        report_output,
        "--html-output",
        html_output,
        "--state-dir",
        state_dir,
        "--format",
        "json",
    ]
    if source_registry and source_registry.exists():
        cmd.extend(["--source-registry", source_registry])
    if items_json:
        cmd.extend(["--items-json", items_json])
    return cmd


def daily_report_command(
    *,
    profile: dict[str, Any],
    profile_file: Path,
    run_dir: Path,
    state_dir: Path,
    source_args: list[str],
    hours: int,
    items_json: str | None,
    allow_incomplete: bool,
) -> list[str | Path]:
    report_output = run_dir / "report.md"
    cmd: list[str | Path] = [
        sys.executable,
        PROJECT_ROOT / "scripts" / "daily_report.py",
        *source_args,
        "--profile",
        profile_file,
        "--hours",
        str(hours),
        "--output-dir",
        run_dir,
        "--report-output",
        report_output,
        "--html",
        "--state-dir",
        state_dir,
        "--format",
        "json",
    ]
    if profile.get("next_scan_note"):
        cmd.extend(["--next-scan-note", str(profile["next_scan_note"])])
    if items_json:
        cmd.extend(["--items-json", items_json])
    if allow_incomplete:
        cmd.append("--allow-incomplete")
    return cmd


def delivery_targets_for_profile(config: MonitorConfig, profile: dict[str, Any]) -> list[dict[str, Any]]:
    target_ids = profile.get("delivery_targets") or profile.get("delivery_target") or []
    if isinstance(target_ids, str):
        target_ids = [target_ids]
    targets = [config.delivery_targets[item] for item in target_ids if item in config.delivery_targets]
    if targets:
        return targets
    return [target for target in config.delivery_targets.values() if target.get("type") == "telegram_bot"]


def run_delivery(
    *,
    conn,
    run_id_value: str,
    profile_id: str,
    cards: list[dict[str, Any]],
    targets: list[dict[str, Any]],
    mode: str,
    report_path: str | None,
    dashboard_url: str,
) -> tuple[int, list[dict[str, Any]]]:
    candidates = monitor_state.alert_candidates(cards)
    events: list[dict[str, Any]] = []
    if mode == "off":
        return len(candidates), events
    for card in candidates:
        item = card.get("item") if isinstance(card.get("item"), dict) else {}
        for target in targets:
            if target.get("type") != "telegram_bot" or not target.get("enabled", False):
                continue
            text = delivery.build_telegram_alert_text(
                item=item,
                card=card,
                report_url=report_path,
                dashboard_url=dashboard_url,
            )
            attempt = delivery.send_telegram_bot_message(
                target_id=target["id"],
                chat_id=str(target.get("chat_id") or ""),
                text=text,
                mode=mode,
            )
            event = monitor_state.record_alert_event(
                conn,
                run_id=run_id_value,
                card_id=card["card_id"],
                profile_id=profile_id,
                target_id=target["id"],
                status=attempt.status,
                payload={"text": text},
                delivery_attempt=attempt.to_dict(),
            )
            events.append(event)
    return len(candidates), events


def write_latest_pointer(output_dir: Path, manifest_path: Path) -> None:
    latest = output_dir / "latest"
    latest.mkdir(parents=True, exist_ok=True)
    pointer = latest / "run-manifest.path"
    pointer.write_text(str(manifest_path), encoding="utf-8")


def run_profile(args: argparse.Namespace) -> int:
    config_path = root_path(args.config)
    try:
        config = load_config(config_path)
    except ValueError as exc:
        agent_cli.emit_error(
            args,
            code="profile_run_config_invalid",
            message=str(exc),
            retryable=False,
            next_step="Fix .tgcs/profiles.toml or pass --config with a valid profile_run_config_v1 file.",
        )
        return agent_cli.EXIT_VALIDATION
    profile = config.profiles.get(args.profile_id)
    if not profile:
        agent_cli.emit_error(
            args,
            code="profile_not_found",
            message=f"Profile id not found: {args.profile_id}",
            retryable=False,
            next_step="Add the profile to .tgcs/profiles.toml or choose an existing profile id.",
        )
        return agent_cli.EXIT_VALIDATION
    if not profile.get("enabled", True):
        agent_cli.emit_error(
            args,
            code="profile_disabled",
            message=f"Profile is disabled: {args.profile_id}",
            retryable=False,
            next_step="Enable the profile before running it.",
        )
        return agent_cli.EXIT_VALIDATION

    started_at = utc_now()
    current_run_id = args.run_id or run_id()
    output_dir = root_path(args.output_dir or config.defaults.get("output_dir", "output"))
    run_dir = output_dir / "runs" / current_run_id
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        agent_cli.emit_error(
            args,
            code="run_id_exists",
            message=f"Run output already exists: {run_dir}",
            retryable=False,
            next_step="Choose a different --run-id or let monitor.py generate one.",
        )
        return agent_cli.EXIT_VALIDATION
    state_dir = root_path(args.state_dir or config.defaults.get("state_dir", ".tgcs/state"))
    db_path = root_path(args.db or config.defaults.get("database", ".tgcs/tgcs.db"))
    dashboard_url = args.dashboard_url or str(config.defaults.get("dashboard_url") or DEFAULT_DASHBOARD_URL)
    profile_file = profile_path(profile)
    if not profile_file.exists():
        agent_cli.emit_error(
            args,
            code="profile_file_not_found",
            message=f"Profile file not found: {profile_file}",
            retryable=False,
            next_step="Create the local profile copy or fix the profile path.",
        )
        return agent_cli.EXIT_VALIDATION

    source_registry = root_path(profile.get("source_registry") or ".tgcs/sources.json")
    if args.scan_input:
        cmd = report_command_for_scan_input(
            scan_input=root_path(args.scan_input),
            profile_file=profile_file,
            run_dir=run_dir,
            state_dir=state_dir,
            source_registry=source_registry,
            items_json=args.items_json,
        )
    else:
        source_args = source_input_args(profile, run_dir)
        if not source_args:
            agent_cli.emit_error(
                args,
                code="source_input_missing",
                message="Missing source input for monitor run.",
                retryable=False,
                next_step="Create .tgcs/sources.json, configure source_registry, or provide a channel list.",
            )
            return agent_cli.EXIT_VALIDATION
        cmd = daily_report_command(
            profile=profile,
            profile_file=profile_file,
            run_dir=run_dir,
            state_dir=state_dir,
            source_args=source_args,
            hours=args.hours,
            items_json=args.items_json,
            allow_incomplete=args.allow_incomplete,
        )

    exit_code, payload, stderr = run_json_command(cmd)
    report_data = payload.get("data", {}) if payload and payload.get("ok") else {}
    status = report_data.get("status") or ("complete" if exit_code == 0 else "failed")
    report_path = root_path(report_data.get("report_path"), PROJECT_ROOT) if report_data.get("report_path") else None
    html_path = root_path(report_data.get("html_path"), PROJECT_ROOT) if report_data.get("html_path") else None
    scan_path = root_path(report_data.get("scan_path"), PROJECT_ROOT) if report_data.get("scan_path") else root_path(args.scan_input) if args.scan_input else None
    items = report_data.get("items") if isinstance(report_data.get("items"), list) else []

    conn = monitor_state.connect(db_path)
    monitor_state.upsert_profile(conn, {**profile, "path": str(profile_file)})
    for target in config.delivery_targets.values():
        monitor_state.upsert_delivery_target(conn, target)
    monitor_state.record_run(
        conn,
        {
            "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
            "run_id": current_run_id,
            "profile_id": args.profile_id,
            "status": "running",
            "started_at": started_at,
            "completed_at": None,
            "artifacts": [],
        },
    )

    cards: list[dict[str, Any]] = []
    alert_count = 0
    alert_events: list[dict[str, Any]] = []
    if exit_code == 0 and status != "agent_extraction_required":
        cards = monitor_state.upsert_review_cards(
            conn,
            profile_id=args.profile_id,
            run_id=current_run_id,
            items=items,
            report_path=relative_to_root(report_path) if report_path else None,
            dashboard_url=dashboard_url,
        )
        alert_count, alert_events = run_delivery(
            conn=conn,
            run_id_value=current_run_id,
            profile_id=args.profile_id,
            cards=cards,
            targets=delivery_targets_for_profile(config, profile),
            mode=args.delivery_mode,
            report_path=relative_to_root(report_path) if report_path else None,
            dashboard_url=dashboard_url,
        )

    completed_at = utc_now()
    artifacts = []
    for path, kind in ((scan_path, "scan"), (report_path, "report_markdown"), (html_path, "report_html")):
        if path and path.exists():
            artifacts.append(artifact(path, kind))
    manifest = {
        "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
        "run_id": current_run_id,
        "profile_id": args.profile_id,
        "profile_path": relative_to_root(profile_file),
        "profile_hash": file_hash(profile_file),
        "source_registry_path": relative_to_root(source_registry) if source_registry.exists() else None,
        "source_registry_hash": file_hash(source_registry) if source_registry.exists() else None,
        "scan_window": {"hours": args.hours},
        "source_filters": {
            "topics": profile.get("source_topics") or profile.get("topics") or [],
            "source_ids": profile.get("source_ids") or [],
        },
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "artifacts": artifacts,
        "report_status": status,
        "alert_count": alert_count,
        "review_card_count": len(cards),
        "error_summary": None if exit_code == 0 else {"exit_code": exit_code, "stderr": stderr[-2000:]},
        "delivery_attempts": [event["delivery_attempt"] for event in alert_events],
        "command": [str(part) for part in cmd],
    }
    manifest_path = run_dir / "run-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_latest_pointer(output_dir, manifest_path)
    monitor_state.record_run(conn, manifest)
    conn.close()

    data = {
        "schema_version": "monitor_run_result_v1",
        "status": status,
        "run_id": current_run_id,
        "manifest_path": relative_to_root(manifest_path),
        "db_path": relative_to_root(db_path),
        "report_path": relative_to_root(report_path) if report_path else None,
        "html_path": relative_to_root(html_path) if html_path else None,
        "review_card_count": len(cards),
        "alert_count": alert_count,
        "delivery_attempts": [event["delivery_attempt"] for event in alert_events],
        "extraction_request_path": report_data.get("extraction_request_path") or report_data.get("request_path"),
        "items_output_path": report_data.get("items_output_path"),
    }
    if agent_cli.is_json_format(args):
        if exit_code == 0:
            agent_cli.print_json(agent_cli.envelope_success(data))
        else:
            agent_cli.print_json(
                agent_cli.envelope_error(
                    code="monitor_run_failed",
                    message=f"Monitor run failed with exit code {exit_code}.",
                    retryable=exit_code in {agent_cli.EXIT_RUNTIME, agent_cli.EXIT_INCOMPLETE},
                    next_step="Inspect the run manifest and rerun the failing scan/report command if needed.",
                    details=data,
                )
            )
    else:
        print(f"Monitor run saved: {manifest_path}")
    return exit_code


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
        text="TGCS delivery test.",
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
source_registry = ".tgcs/sources.json"
channel_list = "channel_lists/example.txt"
source_topics = ["market-news"]
alert_rule = "high_new_or_changed"
delivery_targets = ["telegram-bot-default"]
dashboard_visible = true

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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run v0.5-alpha TGCS profile monitors.", allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init-config", help="Write a starter .tgcs/profiles.toml.")
    init.add_argument("--config", default=".tgcs/profiles.toml")
    init.add_argument("--force", action="store_true")
    agent_cli.add_format_argument(init)
    init.set_defaults(func=write_default_config)

    run = subparsers.add_parser("run", help="Run one profile monitor.")
    run.add_argument("--profile-id", default=DEFAULT_PROFILE_ID)
    run.add_argument("--config", default=".tgcs/profiles.toml")
    run.add_argument("--db")
    run.add_argument("--output-dir")
    run.add_argument("--state-dir")
    run.add_argument("--run-id")
    run.add_argument("--hours", type=int, default=24)
    run.add_argument("--scan-input", type=Path, help="Use an existing JSONL scan file instead of scanning Telegram.")
    run.add_argument("--items-json", help="Use semantic_items_v1 JSON for report generation.")
    run.add_argument("--dashboard-url", default=DEFAULT_DASHBOARD_URL)
    run.add_argument("--delivery-mode", choices=("off", "dry-run", "live"), default="dry-run")
    run.add_argument("--allow-incomplete", action="store_true")
    agent_cli.add_format_argument(run)
    run.set_defaults(func=run_profile)

    delivery_parser = subparsers.add_parser("delivery-test", help="Test a delivery adapter.")
    delivery_subparsers = delivery_parser.add_subparsers(dest="delivery_command", required=True)
    bot = delivery_subparsers.add_parser("telegram-bot", help="Send or dry-run a Telegram bot test.")
    bot.add_argument("--target-id", default="telegram-bot-default")
    bot.add_argument("--chat-id")
    bot.add_argument("--delivery-mode", choices=("dry-run", "live"), default="dry-run")
    agent_cli.add_format_argument(bot)
    bot.set_defaults(func=test_telegram_bot)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
