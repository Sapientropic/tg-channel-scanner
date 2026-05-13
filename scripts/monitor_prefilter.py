"""Cheap keyword prefiltering for high-frequency monitor lanes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PREFILTER_TEXT_FIELDS = ("text", "message", "raw_text", "caption", "ocr_text", "media_text")



def prefilter_keywords(profile: dict[str, Any]) -> list[str]:
    raw_keywords = profile.get("prefilter_keywords") or []
    if isinstance(raw_keywords, str):
        raw_keywords = [raw_keywords]
    if not isinstance(raw_keywords, list):
        return []
    keywords: list[str] = []
    seen: set[str] = set()
    for keyword in raw_keywords:
        text = str(keyword or "").strip()
        marker = text.casefold()
        if not text or marker in seen:
            continue
        keywords.append(text)
        seen.add(marker)
    return keywords



def semantic_max_messages(profile: dict[str, Any]) -> int | None:
    raw_value = profile.get("semantic_max_messages")
    if raw_value in {None, ""}:
        return None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    # The fast interrupt lane should keep LLM batches small. If this is removed,
    # 30+ keyword hits can push Flash/Pro into multi-second tail latency even
    # when prompt cache hits; use a separate backfill/audit lane for exhaustive
    # catch-up instead of silently widening high-frequency alert batches.
    return value if value > 0 else None



def semantic_max_tokens(profile: dict[str, Any]) -> int | None:
    raw_value = profile.get("semantic_max_tokens")
    if raw_value in {None, ""}:
        return None
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None



def message_text_for_prefilter(message: dict[str, Any]) -> str:
    pieces: list[str] = []
    for field in PREFILTER_TEXT_FIELDS:
        value = message.get(field)
        if isinstance(value, str):
            pieces.append(value)
        elif isinstance(value, list):
            pieces.extend(str(item) for item in value if item)
    return "\n".join(pieces)



def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if not text:
                continue
            try:
                item = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows



def keyword_prefilter_matches(
    scan_path: Path,
    keywords: list[str],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    lowered = [(keyword, keyword.casefold()) for keyword in keywords if keyword.strip()]
    counts = {keyword: 0 for keyword, _ in lowered}
    matches: list[dict[str, Any]] = []
    for message in load_jsonl(scan_path):
        haystack = message_text_for_prefilter(message).casefold()
        matched = [keyword for keyword, marker in lowered if marker and marker in haystack]
        if not matched:
            continue
        for keyword in matched:
            counts[keyword] += 1
        copy = dict(message)
        # This is a cheap gate, not a ranking signal. Downstream LLM/report rules
        # still decide whether the item is high-value enough to interrupt.
        copy["monitor_prefilter"] = {"matched_keywords": matched}
        matches.append(copy)
    return matches, {keyword: count for keyword, count in counts.items() if count > 0}



def write_prefiltered_scan(
    *,
    source_scan_path: Path,
    run_dir: Path,
    matches: list[dict[str, Any]],
    keywords: list[str],
    keyword_counts: dict[str, int],
) -> Path:
    filtered_path = run_dir / "prefiltered-scan.jsonl"
    filtered_path.write_text(
        "".join(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n" for item in matches),
        encoding="utf-8",
    )
    meta_path = source_scan_path.with_suffix(".meta.json")
    filtered_meta = {}
    if meta_path.exists():
        try:
            loaded = json.loads(meta_path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                filtered_meta = loaded
        except json.JSONDecodeError:
            filtered_meta = {}
    original_total = filtered_meta.get("total_messages_collected")
    filtered_meta["output_path"] = str(filtered_path)
    filtered_meta["total_messages_collected"] = len(matches)
    filtered_meta["prefilter"] = {
        "enabled": True,
        "source_scan_path": str(source_scan_path),
        "source_total_messages_collected": original_total,
        "keyword_count": len(keywords),
        "matched_count": len(matches),
        "matched_keywords": keyword_counts,
    }
    filtered_path.with_suffix(".meta.json").write_text(
        json.dumps(filtered_meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return filtered_path
