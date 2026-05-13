"""Generate deterministic Markdown reports from scan JSONL files.

Supports multi-mode operation via profile-driven configuration.
Job-mode is the default; custom modes are activated via the
``## Extraction Schema`` section in the profile Markdown.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

try:
    from scripts import agent_cli, report_diagnostics, source_registry, state_store  # noqa: F401
    from scripts.profile_schema import parse_profile_config
    from scripts.report_extraction import (  # noqa: F401
        DEFAULT_DEEPSEEK_BASE_URL,
        DEFAULT_DEEPSEEK_MODEL,
        DEFAULT_MAX_MESSAGES,
        DEFAULT_MINIMAX_BASE_URL,
        DEFAULT_MINIMAX_CN_BASE_URL,
        DEFAULT_MINIMAX_MODEL,
        DEFAULT_MINIMAX_TOKEN_PLAN_BASE_URL,
        DEFAULT_MODEL,
        LOCAL_AI_SECRET_TARGETS,
        add_token_limit,
        ai_secret,
        api_key_for_provider,
        build_agent_extraction_request,
        build_extraction_prompts,
        cache_metrics_from_usage,
        debug_response_path,
        deepseek_thinking_extra,
        default_extraction_request_path,
        default_items_output_path,
        default_minimax_base_url,
        emit_agent_extraction_required,
        extract_jobs,
        extract_jobs_with_metadata,
        llm_json_failure_code,
        llm_json_failure_diagnostic,
        llm_key_available,
        llm_provider,
        llm_temperature,
        load_semantic_items,
        minimax_thinking_extra,
        normalized_usage,
        parse_extraction_response,
        resolve_llm_settings,
        strip_json_fence,
        write_agent_extraction_request,
        write_prompt_file,
    )
    from scripts.report_markdown import (  # noqa: F401
        action_for_rating,
        build_report,
        bullet_list,
        field_label,
        infer_meta_path,
        load_jsonl,
        load_meta,
        profile_summary,
        render_group,
        render_job,
        table_value,
    )
    from scripts.report_html import (  # noqa: F401
        _render_generic_card,
        _render_job_card,
        render_html,
    )
    from scripts.report_models import ExtractionResult, ReportError, ReportResult  # noqa: F401
    from scripts.report_sources import (  # noqa: F401
        as_list,
        build_message_lookup,
        build_source_summary,
        clean_source_ref,
        coerce_message_lookup,
        deduplicate_jobs,
        decision_status,
        decision_status_label,
        merge_source_refs,
        merge_unique,
        normalize_key,
        normalize_rating,
        origin_refs_for_job,
        parse_markdown_report,
        rating_counts,
        raw_texts_for_job,
        resolve_sources,
        sort_items_for_report,
        source_channels_for_job,
        source_ref_key,
        source_refs_for_job,
        source_strings_for_job,
        match_jobs_to_messages,
    )
    from scripts.summarize import (  # noqa: F401
        positive_int,
        redact_contacts,
        redact_text,
        sort_messages_newest_first,
    )
except ModuleNotFoundError:
    _PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    from scripts import agent_cli, report_diagnostics, source_registry, state_store  # noqa: F401
    from scripts.profile_schema import parse_profile_config
    from scripts.report_extraction import (  # noqa: F401
        DEFAULT_DEEPSEEK_BASE_URL,
        DEFAULT_DEEPSEEK_MODEL,
        DEFAULT_MAX_MESSAGES,
        DEFAULT_MINIMAX_BASE_URL,
        DEFAULT_MINIMAX_CN_BASE_URL,
        DEFAULT_MINIMAX_MODEL,
        DEFAULT_MINIMAX_TOKEN_PLAN_BASE_URL,
        DEFAULT_MODEL,
        LOCAL_AI_SECRET_TARGETS,
        add_token_limit,
        ai_secret,
        api_key_for_provider,
        build_agent_extraction_request,
        build_extraction_prompts,
        cache_metrics_from_usage,
        debug_response_path,
        deepseek_thinking_extra,
        default_extraction_request_path,
        default_items_output_path,
        default_minimax_base_url,
        emit_agent_extraction_required,
        extract_jobs,
        extract_jobs_with_metadata,
        llm_json_failure_code,
        llm_json_failure_diagnostic,
        llm_key_available,
        llm_provider,
        llm_temperature,
        load_semantic_items,
        minimax_thinking_extra,
        normalized_usage,
        parse_extraction_response,
        resolve_llm_settings,
        strip_json_fence,
        write_agent_extraction_request,
        write_prompt_file,
    )
    from scripts.report_markdown import (  # noqa: F401
        action_for_rating,
        build_report,
        bullet_list,
        field_label,
        infer_meta_path,
        load_jsonl,
        load_meta,
        profile_summary,
        render_group,
        render_job,
        table_value,
    )
    from scripts.report_html import (  # noqa: F401
        _render_generic_card,
        _render_job_card,
        render_html,
    )
    from scripts.report_models import ExtractionResult, ReportError, ReportResult  # noqa: F401
    from scripts.report_sources import (  # noqa: F401
        as_list,
        build_message_lookup,
        build_source_summary,
        clean_source_ref,
        coerce_message_lookup,
        deduplicate_jobs,
        decision_status,
        decision_status_label,
        merge_source_refs,
        merge_unique,
        normalize_key,
        normalize_rating,
        origin_refs_for_job,
        parse_markdown_report,
        rating_counts,
        raw_texts_for_job,
        resolve_sources,
        sort_items_for_report,
        source_channels_for_job,
        source_ref_key,
        source_refs_for_job,
        source_strings_for_job,
        match_jobs_to_messages,
    )
    from scripts.summarize import (  # noqa: F401
        positive_int,
        redact_contacts,
        redact_text,
        sort_messages_newest_first,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a deterministic scan report from Telegram messages")
    parser.add_argument("--input", required=True, type=Path, help="Path to scan JSONL file")
    parser.add_argument("--profile", required=True, type=Path, help="Path to candidate profile MD")
    parser.add_argument("--meta", help="Path to scan metadata JSON; defaults to scan_*.meta.json")
    parser.add_argument("--source-registry", type=Path, help="Optional source registry JSON.")
    parser.add_argument("--base-url", help="Custom OpenAI-compatible API base URL")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Model name (default: {DEFAULT_MODEL})")
    parser.add_argument("--max-messages", type=positive_int, default=DEFAULT_MAX_MESSAGES)
    parser.add_argument("--max-tokens", type=positive_int, default=0, help="Max tokens for LLM response (0 = no limit)")
    parser.add_argument("--redact-contact-info", action="store_true")
    parser.add_argument("--output", help="Save report to file (default: print to stdout)")
    parser.add_argument("--html", action="store_true", help="Output HTML instead of Markdown")
    parser.add_argument("--html-output", type=Path, help="Also write an HTML copy while keeping --output as Markdown")
    parser.add_argument("--html-only", type=Path, metavar="REPORT.md",
                        help="Render HTML from an existing Markdown report (no LLM call). "
                        "Requires --input for raw messages.")
    parser.add_argument("--dry-run-prompt", help="Write extraction prompt and do not call the LLM")
    parser.add_argument(
        "--extractor",
        choices=("auto", "llm", "agent"),
        default="auto",
        help="Semantic extractor. auto uses LLM when keys exist, otherwise writes an agent request.",
    )
    parser.add_argument(
        "--items-json",
        help="Use agent-produced semantic_items_v1 JSON from a file, or '-' for stdin.",
    )
    parser.add_argument(
        "--write-extraction-request",
        type=Path,
        help="Write agent_extraction_request_v1 JSON here when --extractor agent is used.",
    )
    parser.add_argument("--next-scan-note", help="Optional footer note, e.g. 'Next scan scheduled for tomorrow.'")
    parser.add_argument("--state-dir", type=Path, help="Opt-in local item memory directory.")
    parser.add_argument("--state-read-only", action="store_true", help="Read state without writing updates.")
    parser.add_argument(
        "--feedback-jsonl",
        action="append",
        type=Path,
        default=[],
        help="Import exported tgcs-feedback-v1 JSONL. Repeat for multiple files.",
    )
    agent_cli.add_format_argument(parser)
    return parser


def main(argv: list[str] | None = None, *, extract_jobs_override=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.input.exists():
        agent_cli.emit_error(
            args,
            code="input_not_found",
            message=f"Input file not found: {args.input}",
            retryable=False,
            next_step="Run scan.py first or pass the correct --input path.",
        )
        return agent_cli.EXIT_VALIDATION
    if not args.profile.exists():
        agent_cli.emit_error(
            args,
            code="profile_not_found",
            message=f"Profile file not found: {args.profile}",
            retryable=False,
            next_step="Pass an existing profile file.",
        )
        return agent_cli.EXIT_VALIDATION

    messages = load_jsonl(args.input)
    profile = args.profile.read_text(encoding="utf-8")
    meta = load_meta(args.input, args.meta)
    profile_config = parse_profile_config(profile)
    source_registry_payload = None
    if args.source_registry:
        try:
            source_registry_payload = source_registry.load_registry(args.source_registry)
            issues = source_registry.validate_registry(source_registry_payload)
            if issues:
                raise ReportError(source_registry.validation_message(issues))
        except (OSError, source_registry.RegistryError, ReportError) as exc:
            agent_cli.emit_error(
                args,
                code="registry_invalid",
                message=str(exc),
                retryable=False,
                next_step="Run source_registry.py validate and fix the registry.",
            )
            return agent_cli.EXIT_VALIDATION

    local_state = None
    feedback_entries: list[dict] = []
    if args.feedback_jsonl and not args.state_dir:
        agent_cli.emit_error(
            args,
            code="state_dir_required",
            message="--feedback-jsonl requires --state-dir so feedback has a local memory target.",
            retryable=False,
            next_step="Pass --state-dir .tgcs/state or omit --feedback-jsonl.",
        )
        return agent_cli.EXIT_VALIDATION
    if args.state_dir:
        try:
            local_state = state_store.load_item_memory(args.state_dir)
            feedback_entries = state_store.load_feedback_jsonl(args.feedback_jsonl)
        except state_store.StateStoreError as exc:
            agent_cli.emit_error(
                args,
                code="state_invalid",
                message=str(exc),
                retryable=False,
                next_step="Fix or remove the local state/feedback file, then rerun report.py.",
            )
            return agent_cli.EXIT_VALIDATION

    if not args.redact_contact_info:
        messages = resolve_sources(messages)
    if args.redact_contact_info:
        messages = redact_contacts(messages)
        profile = redact_text(profile)

    if args.dry_run_prompt:
        system_prompt, user_prompt = build_extraction_prompts(
            messages, profile, meta, args.max_messages, profile_config
        )
        write_prompt_file(args.dry_run_prompt, system_prompt, user_prompt)
        print(f"Prompt saved to {args.dry_run_prompt}", file=sys.stderr)
        agent_cli.emit_success(args, {"prompt_path": str(args.dry_run_prompt)})
        return 0

    if args.items_json and args.html_only:
        agent_cli.emit_error(
            args,
            code="conflicting_inputs",
            message="--items-json cannot be combined with --html-only.",
            retryable=False,
            next_step="Use either --items-json for structured extraction or --html-only for re-rendering.",
        )
        return agent_cli.EXIT_VALIDATION

    llm_metadata: dict | None = None

    # --html-only: skip LLM, parse existing Markdown report
    if args.html_only:
        if not args.html_only.exists():
            agent_cli.emit_error(
                args,
                code="html_only_input_not_found",
                message=f"Markdown report not found: {args.html_only}",
                retryable=False,
                next_step="Pass an existing Markdown report to --html-only.",
            )
            return agent_cli.EXIT_VALIDATION
        if profile_config and profile_config.mode.mode != "job":
            agent_cli.emit_error(
                args,
                code="html_only_custom_mode",
                message="--html-only is not supported for custom mode profiles.",
                retryable=False,
                next_step="Run report.py normally for custom profiles.",
            )
            return agent_cli.EXIT_VALIDATION
        args.html = True  # html-only implies html output
        md_text = args.html_only.read_text(encoding="utf-8")
        raw_jobs = parse_markdown_report(md_text)
        raw_jobs = match_jobs_to_messages(raw_jobs, messages)
        matched = sum(1 for j in raw_jobs if j.get("source_message_ids"))
        print(f"Parsed {len(raw_jobs)} jobs from {args.html_only} ({matched} with original text)", file=sys.stderr)
    else:
        try:
            if args.items_json:
                raw_jobs = load_semantic_items(args.items_json, messages)
            elif extract_jobs_override:
                override_result = extract_jobs_override(
                    messages=messages,
                    profile=profile,
                    meta=meta,
                    base_url=args.base_url,
                    model=args.model,
                    max_messages=args.max_messages,
                    max_tokens=args.max_tokens,
                    profile_config=profile_config,
                )
                if isinstance(override_result, ExtractionResult):
                    raw_jobs = override_result.items
                    llm_metadata = override_result.llm
                else:
                    raw_jobs = override_result
            elif args.extractor == "agent" or (
                args.extractor == "auto" and not llm_key_available()
            ):
                request_path = args.write_extraction_request or default_extraction_request_path(
                    args.output,
                    args.input,
                )
                items_output_path = default_items_output_path(args.output, args.input)
                request = build_agent_extraction_request(
                    messages=messages,
                    profile=profile,
                    meta=meta,
                    input_path=args.input,
                    profile_path=args.profile,
                    output_path=args.output,
                    items_output_path=items_output_path,
                    max_messages=args.max_messages,
                    profile_config=profile_config,
                )
                write_agent_extraction_request(request_path, request)
                emit_agent_extraction_required(args, request_path, items_output_path)
                return agent_cli.EXIT_SUCCESS
            else:
                base_url, model = resolve_llm_settings(args.base_url, args.model)
                extraction = extract_jobs_with_metadata(
                    messages=messages,
                    profile=profile,
                    meta=meta,
                    base_url=base_url,
                    model=model,
                    max_messages=args.max_messages,
                    max_tokens=args.max_tokens,
                    profile_config=profile_config,
                )
                raw_jobs = extraction.items
                llm_metadata = extraction.llm
        except ReportError as exc:
            if args.items_json:
                agent_cli.emit_error(
                    args,
                    code="items_json_invalid",
                    message=str(exc),
                    retryable=False,
                    next_step="Fix the semantic_items_v1 JSON and rerun report.py.",
                )
                return agent_cli.EXIT_VALIDATION
            agent_cli.emit_error(
                args,
                code=exc.code or "llm_provider_error",
                message=str(exc),
                retryable=exc.retryable,
                next_step=exc.next_step or "Check API key, base URL, model, and optional dependencies.",
                details=exc.details,
            )
            if exc.raw_response is not None:
                debug_path = debug_response_path(args.output, args.input)
                debug_path.write_text(exc.raw_response, encoding="utf-8")
                print(f"Raw LLM response saved to {debug_path}", file=sys.stderr)
            return agent_cli.EXIT_RUNTIME

    result = build_report(
        messages=messages,
        profile=profile,
        raw_jobs=raw_jobs,
        meta=meta,
        next_scan_note=args.next_scan_note,
        considered_message_count=min(len(messages), args.max_messages),
        profile_config=profile_config,
        source_registry=source_registry_payload,
        state=local_state,
        feedback_entries=feedback_entries,
    )

    markdown_path = Path(args.output) if args.output and not args.html else None
    html_path = None
    if args.html:
        html_output = render_html(result, profile, meta, args, messages, profile_config)
        if args.output:
            html_path = Path(args.output).with_suffix(".html")
            html_path.write_text(html_output, encoding="utf-8")
            print(f"HTML report saved to {html_path}", file=sys.stderr)
        elif not agent_cli.is_json_format(args):
            print(html_output)
    else:
        if args.output:
            Path(args.output).write_text(result.markdown, encoding="utf-8")
            print(f"Report saved to {args.output}", file=sys.stderr)
        else:
            if agent_cli.is_json_format(args):
                markdown_path = None
            else:
                print(result.markdown)
        if args.html_output:
            html_output = render_html(result, profile, meta, args, messages, profile_config)
            args.html_output.parent.mkdir(parents=True, exist_ok=True)
            args.html_output.write_text(html_output, encoding="utf-8")
            html_path = args.html_output
            print(f"HTML report saved to {args.html_output}", file=sys.stderr)
    if args.state_dir and result.state is not None and not args.state_read_only:
        try:
            state_store.save_item_memory(args.state_dir, result.state)
        except state_store.StateStoreError as exc:
            agent_cli.emit_error(
                args,
                code="state_write_failed",
                message=str(exc),
                retryable=True,
                next_step="Check local state directory permissions and rerun report.py.",
            )
            return agent_cli.EXIT_RUNTIME
    if agent_cli.is_json_format(args):
        data = {
            "input_path": str(args.input),
            "report_path": str(markdown_path) if markdown_path else (str(args.output) if args.output else None),
            "html_path": str(html_path) if html_path else None,
            "stats": result.stats,
            "diagnostics": result.diagnostics,
            "source_summary": result.source_summary,
            "state_summary": result.state_summary,
            "items": result.jobs or [],
        }
        if llm_metadata:
            data["llm"] = llm_metadata
        if not args.output and not args.html and not args.html_output:
            data["markdown"] = result.markdown
        agent_cli.print_json(agent_cli.envelope_success(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
