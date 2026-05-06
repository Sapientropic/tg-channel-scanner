"""Shared media OCR/STT module.

Provides pure async functions for downloading Telegram media to temp files,
processing via OpenAI-compatible vision/STT APIs, and cleaning up.

Used by both scan.py (inline OCR) and ocr_media.py (standalone re-processing).
"""

from __future__ import annotations

import asyncio
import base64
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto

# Media size cap — skip anything larger
MAX_MEDIA_SIZE = 50 * 1024 * 1024  # 50 MB

OCR_PROMPT = (
    "Extract all text from this image exactly as written. "
    "Output only the extracted text, nothing else."
)
VIDEO_PROMPT = (
    "These are frames from a video. "
    "Extract all visible text exactly as written. "
    "Output only the extracted text, nothing else."
)


@dataclass
class OcrConfig:
    """Configuration for OCR/STT API calls."""
    client: object  # openai.OpenAI
    model: str
    stt_client: object  # openai.OpenAI (may be same instance)
    stt_model: str
    language: str | None = None
    video_frames: int = 3
    prompt: str = OCR_PROMPT
    full_video: bool = False  # True = download full video for audio STT


def classify_media(msg) -> str | None:
    """Return 'photo', 'video', 'voice', or None."""
    if not msg.media:
        return None
    if msg.voice:
        return "voice"
    if msg.video:
        return "video"
    if isinstance(msg.media, MessageMediaPhoto):
        return "photo"
    return None


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

async def download_to_temp(
    client: TelegramClient, msg, ext: str, *, thumbnail: bool = False,
) -> Path | None:
    """Download media (or its thumbnail) to a temp file. Caller should unlink when done."""
    if thumbnail:
        # Download the largest thumbnail (tiny, instant)
        fd, path = tempfile.mkstemp(suffix=".jpg")
        os.close(fd)
        try:
            await client.download_media(msg, file=path, thumb=-1)
            if os.path.getsize(path) == 0:
                os.unlink(path)
                return None
            return Path(path)
        except Exception:
            if os.path.exists(path):
                os.unlink(path)
            return None

    # Full media download
    doc = getattr(msg.media, "document", None)
    if doc:
        size = getattr(doc, "size", 0) or 0
        if size > MAX_MEDIA_SIZE:
            return None

    fd, path = tempfile.mkstemp(suffix=ext)
    os.close(fd)
    try:
        await client.download_media(msg, file=path)
        if os.path.getsize(path) == 0:
            os.unlink(path)
            return None
        return Path(path)
    except Exception:
        if os.path.exists(path):
            os.unlink(path)
        return None


# ---------------------------------------------------------------------------
# Vision / STT calls (sync, run via asyncio.to_thread in caller)
# ---------------------------------------------------------------------------

def ocr_image(client, model: str, path: Path, prompt: str) -> str:
    b64 = base64.b64encode(path.read_bytes()).decode()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {
                "url": f"data:image/jpeg;base64,{b64}",
            }},
        ]}],
    )
    return resp.choices[0].message.content or ""


def ocr_video(client, model: str, path: Path, video_frames: int) -> str:
    # Extract key frames via ffmpeg
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=10,
        )
        duration = float(probe.stdout.strip())
    except (ValueError, subprocess.TimeoutExpired, FileNotFoundError):
        duration = 10.0

    with tempfile.TemporaryDirectory() as tmp:
        frames: list[Path] = []
        for i in range(video_frames):
            t = duration * (i + 1) / (video_frames + 1)
            out = Path(tmp) / f"frame_{i}.jpg"
            try:
                subprocess.run(
                    ["ffmpeg", "-ss", str(t), "-i", str(path),
                     "-frames:v", "1", "-q:v", "2", str(out)],
                    capture_output=True, timeout=30,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
            if out.exists() and out.stat().st_size > 0:
                frames.append(out)

        if not frames:
            return ""

        content: list[dict] = [{"type": "text", "text": VIDEO_PROMPT}]
        for fp in frames:
            b64 = base64.b64encode(fp.read_bytes()).decode()
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })

        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
        )
        return resp.choices[0].message.content or ""


def transcribe_audio(
    client, path: Path, stt_model: str, language: str | None,
) -> str:
    with open(path, "rb") as f:
        kwargs: dict = {"model": stt_model, "file": f}
        if language:
            kwargs["language"] = language
        resp = client.audio.transcriptions.create(**kwargs)
    return resp.text


# ---------------------------------------------------------------------------
# High-level: process one message
# ---------------------------------------------------------------------------

async def process_message(
    tg_client: TelegramClient, msg, ocr: OcrConfig,
) -> str | None:
    """Download, OCR/STT one media message. Returns ocr_text or None.

    Videos: downloads thumbnail by default (fast). Use ocr.full_video=True
    to download the full video for audio transcription.
    Temp files are created and deleted within this call.
    """
    group = classify_media(msg)
    if not group:
        return None

    if group == "video" and not ocr.full_video:
        # Default: download thumbnail only (fast, tiny)
        path = await download_to_temp(tg_client, msg, "", thumbnail=True)
        if not path:
            return None
        try:
            return await asyncio.to_thread(
                ocr_image, ocr.client, ocr.model, path, ocr.prompt
            )
        finally:
            path.unlink(missing_ok=True)

    # Full download for photo, voice, or video with full_video=True
    ext = {"voice": ".ogg", "video": ".mp4", "photo": ".jpg"}[group]
    path = await download_to_temp(tg_client, msg, ext)
    if not path:
        return None

    try:
        if group == "photo":
            return await asyncio.to_thread(
                ocr_image, ocr.client, ocr.model, path, ocr.prompt
            )
        elif group == "video":
            # full_video=True: extract frames + OCR, or audio STT
            text = await asyncio.to_thread(
                ocr_video, ocr.client, ocr.model, path, ocr.video_frames
            )
            return text
        elif group == "voice":
            return await asyncio.to_thread(
                transcribe_audio, ocr.stt_client, path, ocr.stt_model, ocr.language
            )
    finally:
        path.unlink(missing_ok=True)
    return None
