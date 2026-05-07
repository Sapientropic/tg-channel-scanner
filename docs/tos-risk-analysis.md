# Telegram ToS Risk Analysis

## TL;DR

Reading your own subscribed Telegram channels at a modest speed is a lower-risk personal use case, but it is not risk-free. Telegram can rate-limit or restrict accounts, and Telegram API use is also subject to Telegram's API Terms of Service, including the separate content licensing and AI scraping restrictions.

## What's Allowed

- Reading messages from channels you've joined via your own account
- Automated summaries for personal use (job hunting, news digests)
- Scanning many channels (50+, even 100+) with proper delays between reads
- Using your own long-standing account with a real phone number

## What's NOT Allowed

- **Bulk data collection** for AI training, resale, or redistribution
- **Using Telegram data to train, fine-tune, enhance, or deploy AI/ML models**
- **Aggressive polling** without respecting rate limits (FloodWaitError)
- **Scraping channels you haven't joined** at scale
- **Selling or redistributing** scraped message data
- **Spamming** — sending automated messages to users/groups

## Real Risk Assessment

### Lower Risk (what this tool is designed for)

Reading messages from your own subscribed channels for personal monitoring with delays between requests. Keep the scope narrow, avoid redistribution, and respect any `FloodWaitError` returned by Telegram.

**Evidence and caveats:**
- Telethon documents `FloodWaitError.seconds` as the wait time Telegram returns for repeated requests
- Telethon's own docs say exact limits are not public and depend on many factors
- Telegram says accounts using unofficial API clients are monitored for ToS violations

### High Risk (avoid these)

- **New accounts + virtual phone numbers**: These get banned quickly ([Telethon #3955](https://github.com/LonamiWebs/Telethon/issues/3955))
- **Aggressive polling without delays**: Triggers FloodWaitError, can escalate to temporary restrictions
- **Sending automated messages**: The fastest path to account ban
- **Bulk data export for redistribution**: Against ToS

## Rate Limiting (FloodWaitError)

Telegram enforces rate limits per-account. When you hit them, you get a `FloodWaitError` with a wait time in seconds.

These are practical starting points, not official Telegram limits:

| Action | Conservative starting point |
|--------|----------------------|
| Read messages (`get_messages`) | ~1 request/second |
| Get channel info (`get_entity`) | Cache results; avoid repeatedly resolving the same channel |
| General API calls | Keep bursts small and respect `FloodWaitError.seconds` |

The scanner defaults to a 1-second delay between channels (`SCAN_DELAY=1`). If Telegram asks for a wait longer than `SCAN_MAX_FLOOD_WAIT_SECONDS`, the channel fails instead of silently sleeping for a long time.

## Third-party LLM/OCR Uploads

Report generation sends the selected message text and profile to your configured LLM provider. Media OCR/STT is off by default; when enabled, image/video thumbnails or audio may be sent to the configured OCR/STT provider. Full-video processing is explicit-only (`--ocr-full-video` in `scan.py`, `--full-video` in `ocr_media.py`) and may upload extracted frames, audio, or transcripts. Check the provider's privacy, retention, and billing terms before enabling it.

## Reading All Subscribed Channels

This is a legitimate use case. If you want to scan all your channels:

1. **Keep the 1-second delay** between channels (default in scan scripts)
2. **Handle FloodWaitError** — if Telegram says "wait X seconds", respect it
3. **Use your real account** — not a newly created one or one with a virtual number
4. **Scan frequency** — on-demand scans are always fine; automated daily scans are also fine

To scan all your subscribed channels, export them first:

1. Manually collect usernames from Telegram's channel info pages, or export your Telegram data and copy channel usernames from that local export.
2. Put one username per line in `channel_lists/all.txt`.
3. Keep `SCAN_DELAY` at 1 second or higher for large lists.

## What Happens If You Exceed Rate Limits

1. **FloodWaitError**: Server returns a wait time. Wait and retry if it is within your configured threshold.
2. **Temporary restriction**: If you repeatedly ignore FloodWaitError, your account may be restricted for a few hours.
3. **Account ban**: Only for severe abuse (spam, bulk data harvesting, using virtual numbers).

Our scan scripts redirect errors to `*.errors.log` — check this file if channels fail.

## Legal Disclaimer

This analysis is based on Telegram API documentation, Telethon documentation, community reports, and open-source project experience as of 2026-05-06. Telegram may update their policies at any time. Use this tool responsibly and do not treat this document as legal advice.

Sources:
- [Telegram API Terms of Service](https://core.telegram.org/api/terms)
- [Creating your Telegram Application](https://core.telegram.org/api/obtaining_api_id)
- [Telethon RPC Errors / FloodWaitError](https://docs.telethon.dev/en/stable/concepts/errors.html)
- [Telethon Issue #3955: Account bans](https://github.com/LonamiWebs/Telethon/issues/3955)
- [Stack Overflow: Telethon rate limits](https://stackoverflow.com/questions/76198570)
- [Telebrief: Multi-channel digest tool](https://github.com/belaytzev/Telebrief)
- [tg-channel-digest: Real-time monitoring](https://github.com/Lonky1995/tg-channel-digest)
