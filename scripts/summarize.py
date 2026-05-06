"""
Optional LLM summarizer for scan results.
Requires: openai package (pip install openai)

Usage:
  python summarize.py --input output/scan_XXXX.jsonl --profile profiles/example.md
  OPENAI_API_KEY=sk-xxx python summarize.py --input output/scan_XXXX.jsonl --profile profiles/example.md
  python summarize.py --input output/scan_XXXX.jsonl --profile profiles/example.md --base-url http://localhost:11434/v1

Works with any OpenAI-compatible API:
  - OpenAI (default)
  - DeepSeek (base-url: https://api.deepseek.com/v1)
  - Ollama local (base-url: http://localhost:11434/v1)
  - Anthropic via proxy
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("Install openai package: pip install openai", file=sys.stderr)
    sys.exit(1)

DEFAULT_MAX_MESSAGES = 200


def load_messages(filepath: str) -> list[dict]:
    messages = []
    skipped = 0
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                skipped += 1
    if skipped:
        print(f"Warning: Skipped {skipped} invalid lines", file=sys.stderr)
    return messages


def summarize(
    messages: list[dict],
    profile: str,
    base_url: str | None,
    model: str,
    max_messages: int = DEFAULT_MAX_MESSAGES,
) -> str:
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print(
            "Error: No API key. Set OPENAI_API_KEY or DEEPSEEK_API_KEY environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url=base_url)

    system_prompt = f"""You are a professional job search assistant. Read the candidate profile and Telegram channel messages below.
Filter messages to only include jobs matching the candidate's criteria.
Remove duplicates (same company + title). Rate each match (high/medium/low).
Output a structured report in Markdown.

=== CANDIDATE PROFILE ===
{profile}
"""

    # Truncate by message count, keeping JSON structure intact
    if len(messages) > max_messages:
        truncated = messages[:max_messages]
        note = f"\n\n[Note: Showing {max_messages} of {len(messages)} messages. {len(messages) - max_messages} older messages omitted.]"
        data_text = json.dumps(truncated, ensure_ascii=False)
    else:
        note = ""
        data_text = json.dumps(messages, ensure_ascii=False)

    user_prompt = f"""=== TELEGRAM MESSAGES ({len(messages)} total) ===
{data_text}{note}

Generate a filtered, deduplicated job match report."""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
    except Exception as e:
        print(f"API error: {e}", file=sys.stderr)
        sys.exit(1)

    return response.choices[0].message.content or "No response"


def main():
    parser = argparse.ArgumentParser(description="Summarize scan results with LLM")
    parser.add_argument("--input", required=True, help="Path to scan JSONL file")
    parser.add_argument("--profile", required=True, help="Path to candidate profile MD")
    parser.add_argument("--base-url", help="Custom API base URL (for DeepSeek, Ollama, etc.)")
    parser.add_argument("--model", default="gpt-4o-mini", help="Model name (default: gpt-4o-mini)")
    parser.add_argument("--max-messages", type=int, default=DEFAULT_MAX_MESSAGES, help=f"Max messages to send to LLM (default: {DEFAULT_MAX_MESSAGES})")
    parser.add_argument("--output", help="Save report to file (default: print to stdout)")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    if not Path(args.profile).exists():
        print(f"Error: Profile file not found: {args.profile}", file=sys.stderr)
        sys.exit(1)

    messages = load_messages(args.input)
    print(f"Loaded {len(messages)} messages from {args.input}", file=sys.stderr)

    with open(args.profile, encoding="utf-8") as f:
        profile = f.read()

    result = summarize(
        messages=messages,
        profile=profile,
        base_url=args.base_url,
        model=args.model,
        max_messages=args.max_messages,
    )

    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
        print(f"Report saved to {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()
