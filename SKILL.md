---
name: tg-channel-scanner
description: Use when Codex needs to run TG Channel Scanner workflows: diagnose Telegram/LLM setup, maintain source registry, scan Telegram channels, generate Markdown/HTML reports, inspect source health, or explain report feedback/provenance.
---

# TG Channel Scanner Agent Workflow

Use the JSON contract for agent calls. Human progress is not a stable API.
For a human at a terminal, prefer the short facade commands: `tgcs init`,
`tgcs login`, and `tgcs run`. Do not treat `tgcs` human output as the agent API.

## Safe Order

1. Diagnose first:
   `python scripts/doctor.py --source-registry .tgcs/sources.json --profile profiles/templates/market-news.md --output-dir output --format json`
2. Validate or inspect sources:
   `python scripts/source_registry.py validate --source-registry .tgcs/sources.json --format json`
   `python scripts/source_registry.py list --source-registry .tgcs/sources.json --format json`
3. Import legacy lists only when asked:
   `python scripts/source_registry.py import-list channel_lists/example.txt --source-registry .tgcs/sources.json --format json --dry-run`
4. Scan with registry:
   `python scripts/scan.py --source-registry .tgcs/sources.json --hours 24 --output output/scan.jsonl --format json`
5. Generate report:
   `python scripts/report.py --input output/scan.jsonl --profile profiles/templates/market-news.md --output output/report.md --html-output output/report.html --source-registry .tgcs/sources.json --format json`
6. After semantic items exist, optionally enable cross-run decision memory:
   `python scripts/report.py --input output/scan.jsonl --profile profiles/templates/market-news.md --items-json output/extracted-items.json --output output/report.md --html-output output/report.html --source-registry .tgcs/sources.json --state-dir .tgcs/state --format json`
   Use `--state-read-only` when inspecting history without updating it. Use repeated
   `--feedback-jsonl <path>` flags to import exported local report feedback.
7. If report returns `agent_extraction_required`, do the semantic extraction as the agent:
   - Read `request_path`.
   - Write `semantic_items_v1` JSON to `items_output_path`.
   - Rerun report:
     `python scripts/report.py --input output/scan.jsonl --profile profiles/templates/market-news.md --items-json output/extracted-items.json --output output/report.md --html-output output/report.html --source-registry .tgcs/sources.json --format json`

## Safety Boundaries

- Do not perform interactive Telegram login. If JSON output returns an auth/session error, ask the user to run a human-mode scan once.
- For human handoff, ask the user to run `tgcs login`; it retries empty or
  rejected phone/code/password input and writes the normal local Telethon
  session.
- Do not print API keys, Telegram session strings, channel lists from private `.tgcs/`, or raw local paths unless needed for the current run.
- Treat `.tgcs/sources.json` as private local state. It is ignored by git.
- Prefer source registry for source maintenance, but keep legacy `channel_lists/*.txt` commands valid.
- Source health and pruning hints are single-run signals only. Do not claim trend evidence without history.
- Decision intelligence history exists only when `--state-dir` is supplied. The
  `item_memory_v1` file stores item keys, refs, counters, fingerprints, rating
  history, and feedback counts; never persist raw Telegram text or feedback note
  bodies there.
- `tgcs run` is a human convenience layer and supplies `--state-dir .tgcs/state`
  by default. Low-level agent calls remain explicit.
- When no LLM key exists, prefer the agent fallback request instead of asking the user to configure a key.
- `--extractor agent` never calls an external LLM provider; it writes a local extraction request for the current agent to handle.
- Agent-produced items must preserve `source_message_refs`; do not invent refs or bind refs across channels.

Detailed CLI contract: `docs/agent-cli-contract.md`.
