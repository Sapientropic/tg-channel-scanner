"""Human-oriented TG Channel Scanner CLI facade.

The lower-level scripts keep their explicit agent contract.  This facade is
for people who run the same local workflow repeatedly: it chooses stable local
defaults, keeps v0.4 state on by default, and delegates to the existing scripts
without changing their machine-readable interfaces.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_DIR = ".tgcs"
CONFIG_NAME = "config.toml"
DEFAULT_PROFILE = "market-news"
PROFILE_ALIASES = {
    "jobs": "profiles/templates/jobs.md",
    "airdrops": "profiles/templates/airdrops.md",
    "market-news": "profiles/templates/market-news.md",
    "research-leads": "profiles/templates/research-leads.md",
    "competitor-monitoring": "profiles/templates/competitor-monitoring.md",
}


def _python() -> str:
    return sys.executable


def _root_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _script(name: str) -> Path:
    return PROJECT_ROOT / "scripts" / name


def _local_path(*parts: str) -> Path:
    return PROJECT_ROOT / LOCAL_DIR / Path(*parts)


def _read_config() -> dict[str, Any]:
    path = _local_path(CONFIG_NAME)
    if not path.exists():
        return {}
    with path.open("rb") as fh:
        payload = tomllib.load(fh)
    return payload if isinstance(payload, dict) else {}


def _configured_path(config: dict[str, Any], key: str, default: str) -> Path:
    value = str(config.get(key) or default)
    return _root_path(value)


def _profile_path(value: str | None, config: dict[str, Any]) -> Path:
    profile = value or str(config.get("profile") or DEFAULT_PROFILE)
    if profile in PROFILE_ALIASES:
        return _root_path(PROFILE_ALIASES[profile])
    if profile.endswith(".md") or "/" in profile or "\\" in profile:
        return _root_path(profile)
    return _root_path(f"profiles/templates/{profile}.md")


def _default_source_registry(config: dict[str, Any]) -> Path:
    return _configured_path(config, "source_registry", f"{LOCAL_DIR}/sources.json")


def _default_channel_list(config: dict[str, Any]) -> Path:
    return _configured_path(config, "channel_list", "channel_lists/example.txt")


def _default_output_dir(config: dict[str, Any]) -> Path:
    return _configured_path(config, "output_dir", "output")


def _default_state_dir(config: dict[str, Any]) -> Path:
    return _configured_path(config, "state_dir", f"{LOCAL_DIR}/state")


def _source_args(args: argparse.Namespace, config: dict[str, Any]) -> list[str]:
    if getattr(args, "source_registry", None):
        return ["--source-registry", str(_root_path(args.source_registry))]
    registry = _default_source_registry(config)
    if registry.exists():
        return ["--source-registry", str(registry)]
    channel_list = _root_path(getattr(args, "channel_list", None) or _default_channel_list(config))
    return [str(channel_list)]


def _run(cmd: list[str | Path]) -> int:
    completed = subprocess.run([str(part) for part in cmd], check=False)
    return completed.returncode


def _write_default_config(path: Path, *, force: bool = False) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                'profile = "market-news"',
                'channel_list = "channel_lists/example.txt"',
                'source_registry = ".tgcs/sources.json"',
                'output_dir = "output"',
                'state_dir = ".tgcs/state"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def run_demo(args: argparse.Namespace) -> int:
    output = _root_path(args.output or "output/demo-report.md")
    output.parent.mkdir(parents=True, exist_ok=True)
    return _run(
        [
            _python(),
            _script("report.py"),
            "--input",
            PROJECT_ROOT / "docs/demo/fixtures/demo-scan.jsonl",
            "--profile",
            PROJECT_ROOT / "docs/demo/fixtures/demo-profile.md",
            "--html-only",
            PROJECT_ROOT / "docs/demo/fixtures/demo-report.md",
            "--output",
            output,
        ]
    )


def run_init(args: argparse.Namespace) -> int:
    config_path = _local_path(CONFIG_NAME)
    _local_path().mkdir(parents=True, exist_ok=True)
    _default_output_dir({}).mkdir(parents=True, exist_ok=True)
    _default_state_dir({}).mkdir(parents=True, exist_ok=True)
    _write_default_config(config_path, force=args.force)

    registry = _root_path(args.source_registry or f"{LOCAL_DIR}/sources.json")
    channel_list = _root_path(args.channel_list or "channel_lists/example.txt")
    if registry.exists() and not args.force:
        print(f"Local config ready: {config_path}")
        print(f"Source registry already exists: {registry}")
        return 0
    if not channel_list.exists():
        print(f"Local config ready: {config_path}")
        print(f"Channel list not found, skipped source import: {channel_list}", file=sys.stderr)
        return 0
    return _run(
        [
            _python(),
            _script("source_registry.py"),
            "import-list",
            channel_list,
            "--source-registry",
            registry,
        ]
    )


def run_login(args: argparse.Namespace) -> int:
    cmd: list[str | Path] = [_python(), _script("scan.py"), "--login-only"]
    if args.format == "json":
        cmd.extend(["--format", "json"])
    return _run(cmd)


def run_doctor(args: argparse.Namespace) -> int:
    config = _read_config()
    cmd: list[str | Path] = [
        _python(),
        _script("doctor.py"),
        *_source_args(args, config),
        "--profile",
        _profile_path(args.profile, config),
        "--output-dir",
        _root_path(args.output_dir or _default_output_dir(config)),
    ]
    if args.online_telegram:
        cmd.append("--online-telegram")
    if args.format == "json":
        cmd.extend(["--format", "json"])
    return _run(cmd)


def run_daily(args: argparse.Namespace) -> int:
    config = _read_config()
    cmd: list[str | Path] = [
        _python(),
        _script("daily_report.py"),
        *_source_args(args, config),
        "--profile",
        _profile_path(args.profile, config),
        "--hours",
        str(args.hours),
        "--output-dir",
        _root_path(args.output_dir or _default_output_dir(config)),
    ]
    if not args.no_html:
        cmd.append("--html")
    if not args.no_state:
        cmd.extend(["--state-dir", str(_root_path(args.state_dir or _default_state_dir(config)))])
    if args.state_read_only:
        cmd.append("--state-read-only")
    for feedback_path in args.feedback_jsonl:
        cmd.extend(["--feedback-jsonl", str(_root_path(feedback_path))])
    if args.items_json:
        cmd.extend(["--items-json", args.items_json])
    if args.extractor:
        cmd.extend(["--extractor", args.extractor])
    if args.allow_incomplete:
        cmd.append("--allow-incomplete")
    if args.format == "json":
        cmd.extend(["--format", "json"])
    return _run(cmd)


def run_sources(args: argparse.Namespace) -> int:
    registry = _root_path(args.source_registry or f"{LOCAL_DIR}/sources.json")
    cmd: list[str | Path] = [_python(), _script("source_registry.py")]
    if args.sources_command == "import":
        cmd.extend(["import-list", _root_path(args.channel_list), "--source-registry", registry])
        if args.dry_run:
            cmd.append("--dry-run")
    elif args.sources_command == "list":
        cmd.extend(["list", "--source-registry", registry])
    elif args.sources_command == "validate":
        cmd.extend(["validate", "--source-registry", registry])
    elif args.sources_command == "export":
        cmd.extend(["export-list", "--source-registry", registry, "--output", _root_path(args.output)])
    else:
        raise AssertionError(f"Unsupported sources command: {args.sources_command}")
    if args.format == "json":
        cmd.extend(["--format", "json"])
    return _run(cmd)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tgcs",
        description="Human-friendly TG Channel Scanner command facade.",
        allow_abbrev=False,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="Render the offline demo report.")
    demo.add_argument("--output", help="Markdown output path. Defaults to output/demo-report.md.")
    demo.set_defaults(func=run_demo)

    init = subparsers.add_parser("init", help="Create .tgcs defaults and import the example sources.")
    init.add_argument("--channel-list", help="Channel list to import into .tgcs/sources.json.")
    init.add_argument("--source-registry", help="Source registry path. Defaults to .tgcs/sources.json.")
    init.add_argument("--force", action="store_true", help="Overwrite local config and source registry.")
    init.set_defaults(func=run_init)

    login = subparsers.add_parser("login", help="Complete Telegram login without scanning.")
    login.add_argument("--format", choices=("human", "json"), default="human")
    login.set_defaults(func=run_login)

    doctor = subparsers.add_parser("doctor", help="Run first-run checks with local defaults.")
    doctor.add_argument("--profile", help="Profile alias or path. Defaults to market-news.")
    doctor.add_argument("--source-registry", help="Source registry path.")
    doctor.add_argument("--channel-list", help="Channel list path used when no registry exists.")
    doctor.add_argument("--output-dir", help="Output directory. Defaults to output.")
    doctor.add_argument("--online-telegram", action="store_true")
    doctor.add_argument("--format", choices=("human", "json"), default="human")
    doctor.set_defaults(func=run_doctor)

    run = subparsers.add_parser("run", help="Scan sources and generate today's report.")
    run.add_argument("--profile", help="Profile alias or path. Defaults to market-news.")
    run.add_argument("--hours", type=int, default=24)
    run.add_argument("--source-registry", help="Source registry path.")
    run.add_argument("--channel-list", help="Channel list path used when no registry exists.")
    run.add_argument("--output-dir", help="Output directory. Defaults to output.")
    run.add_argument("--no-html", action="store_true", help="Skip HTML output.")
    run.add_argument("--no-state", action="store_true", help="Disable v0.4 local decision memory.")
    run.add_argument("--state-dir", help="State directory. Defaults to .tgcs/state.")
    run.add_argument("--state-read-only", action="store_true")
    run.add_argument("--feedback-jsonl", action="append", default=[])
    run.add_argument("--items-json")
    run.add_argument("--extractor", choices=("auto", "llm", "agent"))
    run.add_argument("--allow-incomplete", action="store_true")
    run.add_argument("--format", choices=("human", "json"), default="human")
    run.set_defaults(func=run_daily)

    sources = subparsers.add_parser("sources", help="Maintain the local source registry.")
    source_subparsers = sources.add_subparsers(dest="sources_command", required=True)
    source_import = source_subparsers.add_parser("import", help="Import a channel list.")
    source_import.add_argument("channel_list")
    source_import.add_argument("--source-registry")
    source_import.add_argument("--dry-run", action="store_true")
    source_import.add_argument("--format", choices=("human", "json"), default="human")
    source_import.set_defaults(func=run_sources)
    source_list = source_subparsers.add_parser("list", help="List sources.")
    source_list.add_argument("--source-registry")
    source_list.add_argument("--format", choices=("human", "json"), default="human")
    source_list.set_defaults(func=run_sources)
    source_validate = source_subparsers.add_parser("validate", help="Validate sources.")
    source_validate.add_argument("--source-registry")
    source_validate.add_argument("--format", choices=("human", "json"), default="human")
    source_validate.set_defaults(func=run_sources)
    source_export = source_subparsers.add_parser("export", help="Export sources as a channel list.")
    source_export.add_argument("--output", required=True)
    source_export.add_argument("--source-registry")
    source_export.add_argument("--format", choices=("human", "json"), default="human")
    source_export.set_defaults(func=run_sources)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
