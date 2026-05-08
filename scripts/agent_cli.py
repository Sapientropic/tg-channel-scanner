"""Shared agent-facing CLI helpers.

The project keeps user-facing script entry points stable, while agents need a
small deterministic contract for routing failures without scraping prose.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


ENVELOPE_SCHEMA_VERSION = "agent_envelope_v1"

EXIT_SUCCESS = 0
EXIT_RUNTIME = 1
EXIT_INCOMPLETE = 2
EXIT_VALIDATION = 3
EXIT_AUTH = 4

EXIT_CODE_BY_KIND = {
    "runtime": EXIT_RUNTIME,
    "provider": EXIT_RUNTIME,
    "incomplete": EXIT_INCOMPLETE,
    "validation": EXIT_VALIDATION,
    "config": EXIT_VALIDATION,
    "auth": EXIT_AUTH,
}


def add_format_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("human", "json"),
        default="human",
        help="Output format. Use json for agent-readable envelopes.",
    )


def is_json_format(args: argparse.Namespace) -> bool:
    return getattr(args, "format", "human") == "json"


def envelope_success(data: dict[str, Any] | None = None, meta: dict[str, Any] | None = None) -> dict:
    merged_meta = {"schema_version": ENVELOPE_SCHEMA_VERSION}
    if meta:
        merged_meta.update(meta)
    return {
        "ok": True,
        "data": data or {},
        "error": None,
        "meta": merged_meta,
    }


def envelope_error(
    *,
    code: str,
    message: str,
    retryable: bool,
    next_step: str,
    details: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> dict:
    merged_meta = {"schema_version": ENVELOPE_SCHEMA_VERSION}
    if meta:
        merged_meta.update(meta)
    error = {
        "code": code,
        "message": message,
        "retryable": retryable,
        "next_step": next_step,
    }
    if details:
        error["details"] = details
    return {
        "ok": False,
        "data": None,
        "error": error,
        "meta": merged_meta,
    }


def print_json(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def emit_success(
    args: argparse.Namespace,
    data: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    if is_json_format(args):
        print_json(envelope_success(data, meta))


def emit_error(
    args: argparse.Namespace,
    *,
    code: str,
    message: str,
    retryable: bool = False,
    next_step: str = "",
    details: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> None:
    if is_json_format(args):
        print_json(
            envelope_error(
                code=code,
                message=message,
                retryable=retryable,
                next_step=next_step,
                details=details,
                meta=meta,
            )
        )
    else:
        print(f"Error: {message}", file=sys.stderr)
        if next_step:
            print(f"Next: {next_step}", file=sys.stderr)

