"""
Optional LLM summarizer for scan results.
Requires: openai package (pip install openai)

Usage:
  python summarize.py --input output/scan_XXXX.jsonl --profile profiles/example.md
  python summarize.py --input output/scan_XXXX.jsonl --profile profiles/example.md --api-key sk-xxx
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
    print("Install openai package: pip install openai")
    sys.exit(1)


def load_messages(filepath: str) -> list[dict]:
    messages = []
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return messages


def summarize(
    messages: list[dict],
    profile: str,
    api_key: str | None,
    base_url: str | None,
    model: str,
) -> str:
    client = OpenAI(
        api_key=api_key or os.environ.get("OPENAI_API_KEY", "sk-placeholder"),
        base_url=base_url,
    )

    system_prompt = f"""You are a professional job search assistant. Read the candidate profile and Telegram channel messages below.
Filter messages to only include jobs matching the candidate's criteria.
Remove duplicates (same company + title). Rate each match (high/medium/low).
Output a structured report in Markdown.

=== CANDIDATE PROFILE ===
{profile}
"""

    # Truncate if too large (keep under ~100k chars)
    data_text = json.dumps(messages, ensure_ascii=False)
    if len(data_text) > 100000:
        data_text = data_text[:100000] + "\n...[truncated]"

    user_prompt = f"""=== TELEGRAM MESSAGES ({len(messages)} total) ===
{data_text}

Generate a filtered, deduplicated job match report."""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )

    return response.choices[0].message.content or "No response"


def main():
    parser = argparse.ArgumentParser(description="Summarize scan results with LLM")
    parser.add_argument("--input", required=True, help="Path to scan JSONL file")
    parser.add_argument("--profile", required=True, help="Path to candidate profile MD")
    parser.add_argument("--api-key", help="OpenAI-compatible API key")
    parser.add_argument("--base-url", help="Custom API base URL (for DeepSeek, Ollama, etc.)")
    parser.add_argument("--model", default="gpt-4o-mini", help="Model name (default: gpt-4o-mini)")
    parser.add_argument("--output", help="Save report to file (default: print to stdout)")
    args = parser.parse_args()

    messages = load_messages(args.input)
    print(f"Loaded {len(messages)} messages from {args.input}", file=sys.stderr)

    with open(args.profile, encoding="utf-8") as f:
        profile = f.read()

    result = summarize(
        messages=messages,
        profile=profile,
        api_key=args.api_key,
        base_url=args.base_url,
        model=args.model,
    )

    if args.output:
        Path(args.output).write_text(result, encoding="utf-8")
        print(f"Report saved to {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()
