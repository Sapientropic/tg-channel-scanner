# Agent CLI Contract

This document is the stable agent-facing contract for TG Channel Scanner v0.3.
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
python scripts/daily_report.py --source-registry .tgcs/sources.json --profile profiles/templates/market-news.md --html --format json
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
