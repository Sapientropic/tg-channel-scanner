# Agent CLI Contract

This document is the stable agent-facing contract for TG Channel Scanner v0.4.
Human output remains best-effort prose; agents should use `--format json`.

## Envelope: `agent_envelope_v1`

JSON stdout uses this shape:

```json
{
  "ok": true,
  "data": {},
  "error": null,
  "meta": {
    "schema_version": "agent_envelope_v1"
  }
}
```

Failures use a routable error:

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "registry_invalid",
    "message": "Source registry is invalid.",
    "retryable": false,
    "next_step": "Run source_registry.py validate and fix the registry.",
    "details": {}
  },
  "meta": {
    "schema_version": "agent_envelope_v1"
  }
}
```

Progress, diagnostics, and debug details must go to stderr in JSON mode.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Runtime or provider error |
| 2 | Incomplete scan |
| 3 | Validation or configuration error |
| 4 | Auth or Telegram session error |

## Source Registry: `source_registry_v1`

Default path resolution:

1. `--source-registry`
2. `TGCS_SOURCE_REGISTRY`
3. `.tgcs/sources.json`

`.tgcs/` is private local state and ignored by git.

```json
{
  "schema_version": "source_registry_v1",
  "sources": [
    {
      "source_id": "telegram:cointelegraph",
      "username": "cointelegraph",
      "channel_id": null,
      "label": "Cointelegraph",
      "topics": ["market-news"],
      "priority": "normal",
      "expected_language": "en",
      "scan_window_hours": 24,
      "enabled": true,
      "notes": ""
    }
  ]
}
```

## Commands

```powershell
python scripts/source_registry.py import-list channel_lists/example.txt --source-registry .tgcs/sources.json --format json --dry-run
python scripts/source_registry.py validate --source-registry .tgcs/sources.json --format json
python scripts/source_registry.py list --source-registry .tgcs/sources.json --format json
python scripts/source_registry.py export-list --source-registry .tgcs/sources.json --output output/generated-channels.txt --format json

python scripts/doctor.py --source-registry .tgcs/sources.json --profile profiles/templates/market-news.md --output-dir output --format json
python scripts/scan.py --source-registry .tgcs/sources.json --hours 24 --output output/scan.jsonl --format json
python scripts/report.py --input output/scan.jsonl --profile profiles/templates/market-news.md --output output/report.md --html-output output/report.html --source-registry .tgcs/sources.json --format json
python scripts/report.py --input output/scan.jsonl --profile profiles/templates/market-news.md --items-json output/extracted-items.json --state-dir .tgcs/state --feedback-jsonl output/report-feedback.jsonl --format json
python scripts/daily_report.py --source-registry .tgcs/sources.json --profile profiles/templates/market-news.md --html --state-dir .tgcs/state --format json
```

## Agent Semantic Fallback

When no `OPENAI_API_KEY` or `DEEPSEEK_API_KEY` exists, `report.py --extractor auto`
does not fail. It writes a local request for the calling agent:

```powershell
python scripts/report.py --input output/scan.jsonl --profile profiles/templates/market-news.md --output output/report.md --extractor agent --write-extraction-request output/extract-request.json --format json
```

The success envelope uses `data.status = "agent_extraction_required"`:

```json
{
  "ok": true,
  "data": {
    "status": "agent_extraction_required",
    "request_path": "output/extract-request.json",
    "items_output_path": "output/extracted-items.json",
    "next_step": "Extract semantic_items_v1 JSON from request_path, write it to items_output_path, then rerun report.py with --items-json."
  },
  "error": null,
  "meta": {
    "schema_version": "agent_envelope_v1"
  }
}
```

The request file uses `agent_extraction_request_v1` and includes:

- `extraction_contract`
- `agent_instructions`
- `scan_meta`
- `selected_messages`
- prompt text for compatibility with existing profile behavior

The agent writes `semantic_items_v1`:

```json
{
  "schema_version": "semantic_items_v1",
  "items": [
    {
      "source_message_refs": [
        {
          "channel": "cointelegraph",
          "id": 123
        }
      ],
      "rating": "medium",
      "why": "Decision-relevant market signal"
    }
  ]
}
```

Then rerun:

```powershell
python scripts/report.py --input output/scan.jsonl --profile profiles/templates/market-news.md --items-json output/extracted-items.json --output output/report.md --html-output output/report.html --source-registry .tgcs/sources.json --format json
```

`--items-json -` reads the same schema from stdin. Items are validated against
the scan file; unknown `source_message_refs` return `items_json_invalid` with
exit code 3.

## Source Health

`scan.py` writes `source_health` into the metadata sidecar. v0.3 source health is
single-run evidence only:

- `raw_count`
- `kept_count`
- `oldest_message_at`
- `newest_message_at`
- `incomplete`
- `failure`
- `ocr_count`

`report.py` can combine scan meta and the registry to produce single-run pruning
hints: `dormant`, `access_failed`, `incomplete`, `noisy_current_run`,
`duplicate_heavy_current_run`, and `valuable_current_run`.

## Decision Intelligence State

Decision intelligence is explicit opt-in. Agents pass `--state-dir .tgcs/state`
to `report.py` or `daily_report.py` when cross-run memory is desired. The
default remains stateless.

Additional flags:

- `--state-dir PATH`: load and update local item memory at
  `PATH/item-memory.json`.
- `--state-read-only`: use local memory for labels and explanations, but do not
  write updates.
- `--feedback-jsonl PATH`: import exported `tgcs-feedback-v1` JSONL feedback.
  Repeat the flag for multiple files. This requires `--state-dir`.

The state file uses `item_memory_v1`:

```json
{
  "schema_version": "item_memory_v1",
  "updated_at": "2026-05-08T09:00:00Z",
  "items": {
    "profile:abc:topic:coinbase|event:exchange-outage": {
      "item_key": "profile:abc:topic:coinbase|event:exchange-outage",
      "profile_key": "profile:abc",
      "source_message_refs": [{"channel": "cointelegraph", "id": 101}],
      "first_seen_at": "2026-05-08T09:00:00Z",
      "last_seen_at": "2026-05-08T09:00:00Z",
      "seen_count": 1,
      "rating_history": [{"at": "2026-05-08T09:00:00Z", "rating": "high"}],
      "fingerprint": "sha256",
      "feedback_counts": {"keep": 1}
    }
  }
}
```

It must not contain raw Telegram message text, API keys, Telegram sessions, or
feedback note bodies.

Each enriched item can include `decision_state_v1`:

```json
{
  "schema_version": "decision_state_v1",
  "status": "new",
  "signals": ["new"],
  "semantic_cluster": "profile:abc:topic:coinbase|event:exchange-outage",
  "first_seen_at": "2026-05-08T09:00:00Z",
  "last_seen_at": "2026-05-08T09:00:00Z",
  "seen_count": 1,
  "explanations": {
    "novelty": "new",
    "match_confidence": "high",
    "urgency": "today",
    "source_priority": "high",
    "negative_evidence": "No official postmortem yet."
  }
}
```

Possible `status` values: `new`, `seen`, `changed`, `recurring`, and `expired`.
JSON report envelopes add `data.state_summary` and `data.items[*].decision_state`,
for example:

```json
{
  "state_summary": {
    "new": 1,
    "seen": 0,
    "changed": 0,
    "recurring": 0,
    "expired": 0,
    "total": 1
  },
  "items": [
    {
      "topic": "Coinbase",
      "event": "Exchange outage",
      "decision_state": {
        "schema_version": "decision_state_v1",
        "status": "new"
      }
    }
  ]
}
```
