"""Message media projection and optional OCR configuration."""

from __future__ import annotations

import sys
from pathlib import Path
from telethon.tl.types import MessageMediaPhoto

try:
    import openai
except ImportError:
    openai = None  # type: ignore[assignment]

try:
    from scripts.media_ocr import OcrConfig
    from scripts.scan_config import (
        DEFAULT_OPENAI_BASE_URL,
        DEFAULT_OPENAI_OCR_MODEL,
        DEFAULT_XAI_BASE_URL,
        DEFAULT_XAI_OCR_MODEL,
        ScanError,
        ai_secret,
    )
except ModuleNotFoundError:
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    from scripts.media_ocr import OcrConfig
    from scripts.scan_config import (
        DEFAULT_OPENAI_BASE_URL,
        DEFAULT_OPENAI_OCR_MODEL,
        DEFAULT_XAI_BASE_URL,
        DEFAULT_XAI_OCR_MODEL,
        ScanError,
        ai_secret,
    )



def _resolve_ocr_settings(args) -> tuple[str, str, str, str]:
    xai_key = ai_secret("XAI_API_KEY")
    openai_key = ai_secret("OPENAI_API_KEY")
    provider = args.ocr_provider
    if provider is None:
        if xai_key:
            provider = "xai"
        elif openai_key:
            provider = "openai"
        else:
            provider = "xai"

    if provider == "xai":
        if not xai_key:
            raise ScanError("OCR provider xai requires XAI_API_KEY.")
        base_url = args.ocr_base_url or DEFAULT_XAI_BASE_URL
        model = args.ocr_model or DEFAULT_XAI_OCR_MODEL
        return provider, xai_key, base_url, model

    if provider == "openai":
        if not openai_key:
            raise ScanError("OCR provider openai requires OPENAI_API_KEY.")
        base_url = args.ocr_base_url or DEFAULT_OPENAI_BASE_URL
        model = args.ocr_model or DEFAULT_OPENAI_OCR_MODEL
        return provider, openai_key, base_url, model

    api_key = xai_key or openai_key
    if not api_key:
        raise ScanError("OCR provider custom requires XAI_API_KEY or OPENAI_API_KEY.")
    if not args.ocr_base_url:
        raise ScanError("OCR provider custom requires --ocr-base-url.")
    model = args.ocr_model or DEFAULT_OPENAI_OCR_MODEL
    return provider, api_key, args.ocr_base_url, model



def _make_ocr_config(args) -> OcrConfig | None:
    """Create OcrConfig only when OCR is explicitly enabled."""
    if args.no_ocr or not args.ocr:
        return None
    if openai is None:
        raise ScanError("OCR requires optional dependency: pip install -r requirements-llm.txt")

    provider, api_key, base_url, model = _resolve_ocr_settings(args)
    stt_base_url = args.ocr_stt_base_url or base_url
    args.ocr_effective_provider = provider
    args.ocr_effective_base_url = base_url

    vision_client = openai.OpenAI(base_url=base_url, api_key=api_key)
    stt_client = openai.OpenAI(
        base_url=stt_base_url, api_key=api_key,
    )
    return OcrConfig(
        client=vision_client,
        model=model,
        stt_client=stt_client,
        stt_model=args.ocr_stt_model,
        language=args.ocr_language,
        full_video=args.ocr_full_video,
        video_frames=args.ocr_video_frames,
        prompt=args.ocr_prompt,
    )



def _extract_video_meta(msg) -> dict | None:
    """Extract video metadata (duration, size, dimensions) from a message."""
    doc = getattr(msg.media, "document", None)
    if not doc:
        return None
    from telethon.tl.types import DocumentAttributeVideo
    for attr in (doc.attributes or []):
        if isinstance(attr, DocumentAttributeVideo):
            return {
                "video_duration": round(attr.duration, 1),
                "video_width": attr.w,
                "video_height": attr.h,
                "video_file_size": doc.size,
            }
    return None



def message_to_dict(msg, channel_name: str) -> dict:
    media_type = None
    has_photo = False
    media_group = None
    if msg.media:
        media_type = type(msg.media).__name__
        has_photo = isinstance(msg.media, MessageMediaPhoto)
        if msg.voice:
            media_group = "voice"
        elif msg.video:
            media_group = "video"
        elif has_photo:
            media_group = "photo"

    reply_to_msg_id = None
    if msg.reply_to:
        reply_to_msg_id = msg.reply_to.reply_to_msg_id

    forward = None
    origin_message_ref = None
    if msg.forward:
        fwd = msg.forward
        forward = {}
        if hasattr(fwd, 'from_id') and fwd.from_id:
            forward["from_id"] = str(fwd.from_id)
        if getattr(fwd, 'channel_post', None):
            forward["channel_post"] = fwd.channel_post
        if getattr(fwd, 'from_name', None):
            forward["from_name"] = fwd.from_name
        if fwd.date:
            forward["date"] = fwd.date.isoformat()
        if getattr(fwd, "channel_post", None):
            origin_channel = getattr(fwd, "from_name", None) or str(getattr(fwd, "from_id", "") or "")
            if origin_channel:
                origin_message_ref = {
                    "channel": origin_channel,
                    "id": int(fwd.channel_post),
                }

    result = {
        "id": msg.id,
        "message_ref": {"channel": channel_name, "id": msg.id},
        "date": msg.date.isoformat() if msg.date else None,
        "text": msg.text or "",
        "sender_id": msg.sender_id,
        "channel": channel_name,
        "reply_to_msg_id": reply_to_msg_id,
        "has_photo": has_photo,
        "media_type": media_type,
        "media_group": media_group,
        "forward": forward,
    }
    if origin_message_ref:
        result["origin_message_ref"] = origin_message_ref

    # Attach video metadata for "is this worth watching?" decisions
    if media_group == "video":
        video_meta = _extract_video_meta(msg)
        if video_meta:
            result.update(video_meta)

    return result
