"""Source attribution, deduplication, and source summary helpers for reports."""

from __future__ import annotations

import re
from typing import Iterable

from scripts import source_registry


def normalize_key(value: object) -> str:
    text = str(value or "").casefold()
    text = re.sub(r"[^\w]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def as_list(value: object) -> list:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    return [value]


def merge_unique(existing: list, incoming: Iterable) -> list:
    result = list(existing)
    seen = {str(item) for item in result}
    for item in incoming:
        if item in (None, ""):
            continue
        marker = str(item)
        if marker not in seen:
            result.append(item)
            seen.add(marker)
    return result


def source_ref_key(channel: object, message_id: object) -> str:
    return f"{channel}\x1f{message_id}"


def clean_source_ref(channel: object, message_id: object) -> dict | None:
    channel_text = str(channel or "").strip()
    if not channel_text:
        return None
    try:
        parsed_id = int(message_id)
    except (TypeError, ValueError):
        return None
    return {"channel": channel_text, "id": parsed_id}


def build_message_lookup(messages: Iterable[dict] | None) -> dict:
    by_ref: dict[str, dict] = {}
    by_id: dict[int, list[dict]] = {}
    for message in messages or []:
        ref = clean_source_ref(message.get("channel"), message.get("id"))
        if ref is None:
            continue
        by_ref[source_ref_key(ref["channel"], ref["id"])] = message
        by_id.setdefault(ref["id"], []).append(message)
    return {"by_ref": by_ref, "by_id": by_id}


def coerce_message_lookup(message_lookup: dict | None) -> dict:
    if not message_lookup:
        return build_message_lookup([])
    if "by_ref" in message_lookup and "by_id" in message_lookup:
        return message_lookup
    return build_message_lookup(message_lookup.values())


def source_strings_for_job(job: dict) -> list[str]:
    # Prefer pre-split sources list; fall back to splitting raw source string by " / "
    if job.get("sources"):
        sources = list(job["sources"])
    else:
        raw = str(job.get("source") or "")
        sources = [s.strip() for s in raw.split(" / ") if s.strip()]
    return [str(source) for source in merge_unique([], sources)]


def merge_source_refs(existing: Iterable, incoming: Iterable) -> list[dict]:
    result: list[dict] = []
    seen: set[str] = set()
    for item in list(existing or []) + list(incoming or []):
        if not isinstance(item, dict):
            continue
        ref = clean_source_ref(item.get("channel"), item.get("id"))
        if ref is None:
            continue
        marker = source_ref_key(ref["channel"], ref["id"])
        if marker in seen:
            continue
        result.append(ref)
        seen.add(marker)
    return result


def source_refs_for_job(job: dict, message_lookup: dict | None = None) -> list[dict]:
    lookup = coerce_message_lookup(message_lookup)
    explicit_refs = merge_source_refs([], as_list(job.get("source_message_refs")))
    if explicit_refs:
        return explicit_refs

    # Legacy LLM outputs used bare message ids. Those ids are only safe when
    # the job source narrows the channel, or when the id is unique in the scan.
    # Do not silently bind duplicate ids across channels; that was the original
    # bug this compatibility path is designed to avoid.
    sources = set(source_strings_for_job(job))
    refs: list[dict] = []
    for message_id in as_list(job.get("source_message_ids")):
        try:
            parsed_id = int(message_id)
        except (TypeError, ValueError):
            continue
        original_candidates = lookup["by_id"].get(parsed_id, [])
        candidates = original_candidates
        if sources:
            candidates = [
                message
                for message in candidates
                if str(message.get("channel") or "").strip() in sources
            ]
            # Older call sites can pass a single id-indexed message directly.
            # If the id is unique in the available lookup, keeping the legacy
            # binding is safe even when the source label was edited or escaped.
            if not candidates and len(original_candidates) == 1:
                candidates = original_candidates
        elif len(candidates) != 1:
            candidates = []
        for message in candidates:
            ref = clean_source_ref(message.get("channel"), message.get("id"))
            if ref is not None:
                refs.append(ref)
    return merge_source_refs([], refs)


def origin_refs_for_job(job: dict, message_lookup: dict | None = None) -> list[dict]:
    lookup = coerce_message_lookup(message_lookup)
    explicit_refs = merge_source_refs([], as_list(job.get("origin_message_refs")))
    refs: list[dict] = []
    for ref in source_refs_for_job(job, lookup):
        message = lookup["by_ref"].get(source_ref_key(ref["channel"], ref["id"]))
        if not message:
            continue
        origin_ref = message.get("origin_message_ref")
        if isinstance(origin_ref, dict):
            cleaned = clean_source_ref(origin_ref.get("channel"), origin_ref.get("id"))
            if cleaned:
                refs.append(cleaned)
    return merge_source_refs(explicit_refs, refs)


def source_channels_for_job(job: dict, message_lookup: dict | None) -> list[str]:
    sources = source_strings_for_job(job)
    for ref in source_refs_for_job(job, message_lookup):
        sources.append(ref["channel"])
    return [str(source) for source in merge_unique([], sources)]


def raw_texts_for_job(job: dict, message_lookup: dict | None) -> list[tuple[str, str]]:
    lookup = coerce_message_lookup(message_lookup)
    raw_texts: list[tuple[str, str]] = []
    for ref in source_refs_for_job(job, lookup):
        message = lookup["by_ref"].get(source_ref_key(ref["channel"], ref["id"]))
        if message and message.get("text"):
            raw_texts.append((str(message.get("channel", "")), message["text"]))
    return raw_texts


def deduplicate_jobs(
    raw_jobs: list[dict],
    messages: list[dict] | None = None,
    dedup_fields: list[str] | None = None,
) -> tuple[list[dict], int]:
    dedup_fields = dedup_fields or ["company", "role"]
    message_lookup = build_message_lookup(messages)
    deduped: dict[tuple[str, ...], dict] = {}
    order: list[tuple[str, ...]] = []
    duplicates_removed = 0

    for raw in raw_jobs:
        job = dict(raw)
        # Normalise known list/merge fields
        for f in dedup_fields:
            v = str(job.get(f) or f"Unknown {f}").strip()
            job[f] = v
        job["source_message_ids"] = merge_unique([], as_list(raw.get("source_message_ids")))
        job["source_message_refs"] = source_refs_for_job(raw, message_lookup)
        job["origin_message_refs"] = origin_refs_for_job(job, message_lookup)
        job["sources"] = source_channels_for_job(job, message_lookup)
        job["contacts"] = merge_unique([], as_list(raw.get("contact")))
        job["links"] = merge_unique([], as_list(raw.get("link")))
        job["stack"] = [str(item) for item in as_list(raw.get("stack"))]
        job["concerns"] = [str(item) for item in as_list(raw.get("concerns"))]
        job["rating"] = normalize_rating(raw.get("rating"))
        if job["origin_message_refs"]:
            key = tuple(
                f"origin:{ref['channel']}:{ref['id']}" for ref in job["origin_message_refs"]
            )
        else:
            key = tuple(normalize_key(raw.get(f) or "") for f in dedup_fields)
            if all(k == "" for k in key):
                continue

        if key not in deduped:
            deduped[key] = job
            order.append(key)
            continue

        duplicates_removed += 1
        existing = deduped[key]
        existing["source_message_refs"] = merge_source_refs(
            existing.get("source_message_refs", []),
            job.get("source_message_refs", []),
        )
        existing["origin_message_refs"] = merge_source_refs(
            existing.get("origin_message_refs", []),
            job.get("origin_message_refs", []),
        )
        for merge_field in (
            "source_message_ids",
            "sources",
            "contacts",
            "links",
            "stack",
            "concerns",
        ):
            existing[merge_field] = merge_unique(
                existing.get(merge_field, []), job.get(merge_field, [])
            )

    return [deduped[key] for key in order], duplicates_removed


def normalize_rating(value: object) -> str:
    text = str(value or "").strip().casefold()
    if text in {"high", "highly recommended", "apply"}:
        return "high"
    if text in {"medium", "worth investigating", "inspect"}:
        return "medium"
    return "low"


def rating_counts(jobs: list[dict]) -> dict[str, int]:
    counts = {"high": 0, "medium": 0, "low": 0}
    for job in jobs:
        counts[normalize_rating(job.get("rating"))] += 1
    return counts


_STATE_SORT_ORDER = {"changed": 0, "new": 1, "expired": 2, "seen": 3, "recurring": 4}


def decision_status(item: dict) -> str:
    state = item.get("decision_state") if isinstance(item, dict) else None
    if isinstance(state, dict):
        return str(state.get("status") or "").strip().casefold()
    return ""


def decision_status_label(item: dict) -> str:
    status = decision_status(item)
    if not status:
        return ""
    return {
        "new": "New",
        "seen": "Seen",
        "changed": "Changed",
        "recurring": "Recurring",
        "expired": "Expired",
    }.get(status, status.replace("_", " ").title())


def sort_items_for_report(items: list[dict]) -> list[dict]:
    return sorted(
        items,
        key=lambda item: (
            _STATE_SORT_ORDER.get(decision_status(item), 9),
            normalize_key(item.get("why") or ""),
        ),
    )


def _registry_source_for_channel(registry: dict | None, channel: str) -> dict | None:
    lookup = source_registry.source_lookup_by_channel(registry)
    return lookup.get(channel) or lookup.get(channel.casefold())


def _source_id_for_channel(channel: str, registry: dict | None = None) -> str:
    matched = _registry_source_for_channel(registry, channel)
    if matched and matched.get("source_id"):
        return str(matched["source_id"])
    normalized = source_registry.normalize_channel_name(channel)
    if normalized:
        return f"telegram:{normalized.casefold()}"
    return f"telegram:{channel}"


def _source_pruning_hints(source: dict) -> list[str]:
    hints: list[str] = []
    if source.get("failure"):
        hints.append("access_failed")
    if source.get("incomplete"):
        hints.append("incomplete")
    raw_count = int(source.get("raw_count") or 0)
    item_count = int(source.get("report_item_count") or 0)
    duplicate_count = int(source.get("duplicate_count") or 0)
    has_health = bool(source.get("has_health"))
    if has_health and raw_count == 0 and not source.get("failure"):
        hints.append("dormant")
    if has_health and raw_count >= 10 and item_count == 0 and not source.get("failure"):
        hints.append("noisy_current_run")
    if duplicate_count >= max(2, item_count) and raw_count:
        hints.append("duplicate_heavy_current_run")
    if item_count > 0:
        hints.append("valuable_current_run")
    return hints


def build_source_summary(
    jobs: list[dict],
    messages: list[dict],
    meta: dict | None,
    registry: dict | None,
) -> dict:
    summary_by_id: dict[str, dict] = {}
    health_by_id: dict[str, dict] = {}
    for health in (meta or {}).get("source_health", []) or []:
        source_id = str(health.get("source_id") or _source_id_for_channel(health.get("channel", ""), registry))
        health_by_id[source_id] = health

    registry_sources = (registry or {}).get("sources", []) if registry else []
    for source in registry_sources:
        source_id = str(source.get("source_id") or _source_id_for_channel(source_registry.channel_value(source)))
        channel = source_registry.channel_value(source)
        summary_by_id[source_id] = {
            "source_id": source_id,
            "channel": channel,
            "label": source.get("label") or channel,
            "topics": source.get("topics") or [],
            "priority": source.get("priority"),
            "expected_language": source.get("expected_language"),
            "enabled": source.get("enabled", True),
            "raw_count": 0,
            "kept_count": 0,
            "has_health": False,
            "failure": None,
            "incomplete": False,
            "ocr_count": 0,
            "report_item_count": 0,
            "rating_counts": {"high": 0, "medium": 0, "low": 0},
            "duplicate_count": 0,
            "pruning_hints": [],
        }

    for source_id, health in health_by_id.items():
        channel = str(health.get("channel") or "")
        registry_source = _registry_source_for_channel(registry, channel)
        base = summary_by_id.setdefault(
            source_id,
            {
                "source_id": source_id,
                "channel": channel,
                "label": (registry_source or {}).get("label") or channel,
                "topics": (registry_source or {}).get("topics") or [],
                "priority": (registry_source or {}).get("priority"),
                "expected_language": (registry_source or {}).get("expected_language"),
                "enabled": (registry_source or {}).get("enabled", True),
                "report_item_count": 0,
                "rating_counts": {"high": 0, "medium": 0, "low": 0},
                "duplicate_count": 0,
                "pruning_hints": [],
                "has_health": False,
            },
        )
        for field in (
            "raw_count",
            "kept_count",
            "oldest_message_at",
            "newest_message_at",
            "failure",
            "incomplete",
            "ocr_count",
        ):
            base[field] = health.get(field)
        base["has_health"] = True

    message_lookup = build_message_lookup(messages)
    origin_seen_by_source: dict[str, set[str]] = {}
    origin_total_by_source: dict[str, int] = {}
    for job in jobs:
        rating = normalize_rating(job.get("rating"))
        counted_sources: set[str] = set()
        for ref in source_refs_for_job(job, message_lookup):
            source_id = _source_id_for_channel(ref["channel"], registry)
            counted_sources.add(source_id)
            source = summary_by_id.setdefault(
                source_id,
                {
                    "source_id": source_id,
                    "channel": ref["channel"],
                    "label": ref["channel"],
                    "topics": [],
                    "priority": None,
                    "expected_language": None,
                    "enabled": True,
                    "raw_count": 0,
                    "kept_count": 0,
                    "has_health": False,
                    "failure": None,
                    "incomplete": False,
                    "ocr_count": 0,
                    "report_item_count": 0,
                    "rating_counts": {"high": 0, "medium": 0, "low": 0},
                    "duplicate_count": 0,
                    "pruning_hints": [],
                },
            )
            origin_refs = origin_refs_for_job(job, message_lookup)
            if origin_refs:
                origin_total_by_source[source_id] = origin_total_by_source.get(source_id, 0) + 1
                seen = origin_seen_by_source.setdefault(source_id, set())
                for origin_ref in origin_refs:
                    seen.add(source_ref_key(origin_ref["channel"], origin_ref["id"]))
        for source_id in counted_sources:
            source = summary_by_id[source_id]
            source["report_item_count"] += 1
            source["rating_counts"][rating] += 1

    for source_id, total in origin_total_by_source.items():
        unique = len(origin_seen_by_source.get(source_id, set()))
        if source_id in summary_by_id:
            summary_by_id[source_id]["duplicate_count"] = max(0, total - unique)

    sources = list(summary_by_id.values())
    for source in sources:
        source["pruning_hints"] = _source_pruning_hints(source)
    sources.sort(key=lambda item: (str(item.get("label") or ""), str(item.get("source_id") or "")))
    return {
        "sources": sources,
        "totals": {
            "source_count": len(sources),
            "report_item_count": sum(int(source.get("report_item_count") or 0) for source in sources),
        },
    }



# ---------------------------------------------------------------------------
# Source resolution (aggregator → original post)
# ---------------------------------------------------------------------------

# Regex for t.me/channel/123 deep links
_TME_DEEP_LINK = re.compile(r"https?://t\.me/([a-zA-Z]\w{3,})/(\d+)")


def _channel_id_from_peer(peer_str: str) -> int | None:
    """Extract numeric channel_id from PeerChannel(channel_id=123)."""
    m = re.search(r"channel_id=(\d+)", peer_str)
    return int(m.group(1)) if m else None


def resolve_sources(messages: list[dict]) -> list[dict]:
    """Resolve aggregator posts to their original sources.

    For messages with a 'forward' field, construct origin_url from forward
    metadata. Also scans message text for t.me/channel/123 deep links.
    """
    for msg in messages:
        text = msg.get("text", "")
        fwd = msg.get("forward")

        # Method 1: forward metadata
        if fwd:
            channel_post = fwd.get("channel_post")
            from_id_str = fwd.get("from_id", "")

            if channel_post:
                from_cid = _channel_id_from_peer(from_id_str)
                if from_cid:
                    # t.me/c/ links use the raw channel_id (no -100 prefix)
                    origin_url = f"https://t.me/c/{from_cid}/{channel_post}"
                    msg["origin_url"] = origin_url

            from_name = fwd.get("from_name")
            if from_name:
                msg["origin_channel"] = from_name
            origin_channel = from_name or from_id_str
            if origin_channel and channel_post:
                cleaned = clean_source_ref(origin_channel, channel_post)
                if cleaned:
                    msg["origin_message_ref"] = cleaned

        # Method 2: regex t.me/channel/123 links in text
        deep_links = _TME_DEEP_LINK.findall(text)
        if deep_links and "origin_url" not in msg:
            # Use the first deep link as origin
            channel_name, post_id = deep_links[0]
            msg["origin_url"] = f"https://t.me/{channel_name}/{post_id}"
            msg["origin_channel"] = channel_name
            msg["origin_message_ref"] = {"channel": channel_name, "id": int(post_id)}

    return messages


def parse_markdown_report(md_text: str) -> list[dict]:
    """Parse a rendered Markdown report back into structured job dicts.

    Designed for --html-only: re-render HTML from an existing Markdown report
    without calling the LLM again.
    """
    jobs: list[dict] = []
    # Split on job headings: "### N. Role -- Company"
    job_blocks = re.split(r"\n(?=### \d+\.\s)", md_text)
    for block in job_blocks:
        header = re.match(r"### (\d+)\.\s+(.+)", block)
        if not header:
            continue
        title = header.group(2).strip()
        # Split "Role -- Company"
        if " -- " in title:
            role, company = title.split(" -- ", 1)
        else:
            role, company = title, "Unknown"
        job: dict = {"role": role.strip(), "company": company.strip()}

        # Table rows: | **Key** | value |
        for m in re.finditer(r"\|\s*\*\*(\w[\w\s]*?)\*\*\s*\|\s*(.+?)\s*\|", block):
            key = m.group(1).strip().lower()
            val = m.group(2).strip().replace("\\|", "|")
            if key == "company":
                job["company"] = val
            elif key == "role":
                job["role"] = val
            elif key == "location":
                job["location"] = val
            elif key == "salary":
                job["salary"] = val
            elif key == "contact":
                job["contact"] = val
                job["contacts"] = [c.strip() for c in val.split(" / ") if c.strip()]
            elif key == "source":
                job["source"] = val
                job["sources"] = [s.strip() for s in val.split(" / ") if s.strip()]

        # Why it matches
        why_m = re.search(r"\*\*Why it matches\*\*:\s*(.+?)(?=\n\n|\n\*\*|\Z)", block, re.DOTALL)
        if why_m:
            job["why"] = why_m.group(1).strip()

        # Stack
        stack_m = re.search(r"\*\*Stack required\*\*:\s*\n((?:- .+\n?)+)", block)
        if stack_m:
            job["stack"] = [
                line.strip("- ").strip()
                for line in stack_m.group(1).strip().splitlines()
                if line.strip().startswith("-")
            ]

        # Concerns
        concerns_m = re.search(r"\*\*Concerns\*\*:\s*\n((?:- .+\n?)+)", block)
        if concerns_m:
            job["concerns"] = [
                line.strip("- ").strip()
                for line in concerns_m.group(1).strip().splitlines()
                if line.strip().startswith("-")
            ]

        # Action
        action_m = re.search(r"\*\*Action\*\*:\s*\*\*(.+?)\*\*", block)
        if action_m:
            job["action"] = action_m.group(1).strip()

        # Infer rating from action or section context
        action_text = job.get("action", "").lower()
        if "apply" in action_text:
            job["rating"] = "high"
        elif "skip" in action_text:
            job["rating"] = "low"
        elif "inspect" in action_text:
            job["rating"] = "medium"
        else:
            # Fallback: check which section this block is in
            job["rating"] = "medium"

        # Extract origin_url from source text (e.g. "hot_itjobs (origin_url: https://t.me/...)")
        source_text = job.get("source", "")
        origin_m = re.search(r"origin_url:\s*(https?://t\.me/[^\s\)]+)", source_text)
        if origin_m:
            job["origin_url"] = origin_m.group(1)
            # Clean source: remove parenthetical origin info
            job["source"] = re.sub(r"\s*\(originally from[^)]*\)", "", job["source"])
            job["sources"] = [s.strip() for s in job["source"].split(" / ") if s.strip()]

        # Ensure required keys
        for k in ("location", "salary", "contact", "why", "stack", "concerns"):
            job.setdefault(k, "" if k in ("why",) else ([] if k in ("stack", "concerns") else "Not specified"))
        job.setdefault("sources", [])
        job.setdefault("contacts", [])

        jobs.append(job)
    return jobs


def match_jobs_to_messages(jobs: list[dict], messages: list[dict]) -> list[dict]:
    """Fuzzy-match parsed jobs back to raw messages for --html-only mode.

    Uses source channel name + role/company keywords to find matching messages
    and populate source_message_refs/source_message_ids so the HTML renderer can show "View original".
    """
    # Index: channel → [messages]
    by_channel: dict[str, list[dict]] = {}
    for m in messages:
        ch = m.get("channel", "")
        if ch:
            by_channel.setdefault(ch, []).append(m)

    for job in jobs:
        sources = job.get("sources", [])
        company = job.get("company", "").strip()
        role = job.get("role", "").strip()

        # Search in source channels first
        candidates = []
        for src in sources:
            src_clean = re.sub(r"\s*\(originally.*?\)", "", src).strip()
            candidates.extend(by_channel.get(src_clean, []))

        # Fallback: all messages if no source channel matched
        if not candidates:
            candidates = messages

        # Score each candidate by keyword overlap
        keywords = set()
        for word in re.split(r"[^\w一-鿿Ѐ-ӿ]+", company + " " + role):
            w = word.strip().lower()
            if len(w) >= 3 and w not in {"the", "and", "for", "inc", "ltd", "llc", "gmbh", "ooo"}:
                keywords.add(w)

        best_score = 0
        best_ids: list[int] = []
        best_refs: list[dict] = []
        for m in candidates:
            text = (m.get("text") or "").lower()
            score = sum(1 for kw in keywords if kw in text)
            if score > best_score:
                best_score = score
                best_ids = [m["id"]]
                ref = clean_source_ref(m.get("channel"), m.get("id"))
                best_refs = [ref] if ref else []
            elif score == best_score and score > 0 and len(best_ids) < 3:
                mid = m["id"]
                if mid not in best_ids:
                    best_ids.append(mid)
                    ref = clean_source_ref(m.get("channel"), m.get("id"))
                    if ref:
                        best_refs.append(ref)

        if best_ids and best_score >= max(1, int(len(keywords) * 0.6)):
            job["source_message_ids"] = best_ids
            job["source_message_refs"] = best_refs

    return jobs
