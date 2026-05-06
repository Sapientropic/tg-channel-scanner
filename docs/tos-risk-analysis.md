# Telegram ToS Risk Analysis

## TL;DR

Reading your own Telegram channels at a reasonable speed is safe. The main constraint is **FloodWaitError** (server-side rate limiting), not account bans.

## What's Allowed

- Reading messages from channels you've joined via your own account
- Automated summaries for personal use (job hunting, news digests)
- Scanning many channels (50+, even 100+) with proper delays between reads
- Using your own long-standing account with a real phone number

## What's NOT Allowed

- **Bulk data collection** for AI training, resale, or redistribution
- **Aggressive polling** without respecting rate limits (FloodWaitError)
- **Scraping channels you haven't joined** at scale
- **Selling or redistributing** scraped message data
- **Spamming** — sending automated messages to users/groups

## Real Risk Assessment

### Low Risk (what this tool does)

Reading messages from your own subscribed channels at ~1 request/second. This is equivalent to scrolling through Telegram manually, just faster.

**Evidence from the community:**
- Multiple open-source tools ([Telebrief](https://github.com/belaytzev/Telebrief), [tg-channel-digest](https://github.com/Lonky1995/tg-channel-digest)) read hundreds of channels continuously without issues
- Telegram's rate limiter (FloodWaitError) is self-correcting — it tells you how long to wait
- Old accounts with real phone numbers are almost never banned for reading

### High Risk (avoid these)

- **New accounts + virtual phone numbers**: These get banned quickly ([Telethon #3955](https://github.com/LonamiWebs/Telethon/issues/3955))
- **Aggressive polling without delays**: Triggers FloodWaitError, can escalate to temporary restrictions
- **Sending automated messages**: The fastest path to account ban
- **Bulk data export for redistribution**: Against ToS

## Rate Limiting (FloodWaitError)

Telegram enforces rate limits per-account. When you hit them, you get a `FloodWaitError` with a wait time in seconds.

| Action | Approximate Safe Rate |
|--------|----------------------|
| Read messages (`get_messages`) | ~1 request/second |
| Get channel info (`get_entity`) | ~1 request/minute |
| General API calls | ~30 requests per 30 seconds |

**For reading 50 channels at 1-2 seconds each: ~1-2 minutes total. This is well within safe limits.**

Our scan scripts use a 1-second delay between channels (`SCAN_DELAY` env var, adjustable) which is sufficient for most use cases.

## Reading All Subscribed Channels

This is a legitimate use case. If you want to scan all your channels:

1. **Keep the 1-second delay** between channels (default in scan scripts)
2. **Handle FloodWaitError** — if Telegram says "wait X seconds", respect it
3. **Use your real account** — not a newly created one or one with a virtual number
4. **Scan frequency** — on-demand scans are always fine; automated daily scans are also fine

To scan all your subscribed channels, export them first:

```bash
# List all your channels (tgcli)
tg chats --limit 200 | grep "channel" > channel_lists/all.txt
```

Or manually add all channels to a list file in `channel_lists/`.

## What Happens If You Exceed Rate Limits

1. **FloodWaitError**: Server returns a wait time (usually 5-60 seconds). Wait and retry.
2. **Temporary restriction**: If you repeatedly ignore FloodWaitError, your account may be restricted for a few hours.
3. **Account ban**: Only for severe abuse (spam, bulk data harvesting, using virtual numbers).

Our scan scripts redirect errors to `*.errors.log` — check this file if channels fail.

## Legal Disclaimer

This analysis is based on community reports, Telethon documentation, and open-source project experience as of 2026-05. Telegram may update their policies at any time. Use this tool responsibly.

Sources:
- [Telethon FAQ on account bans](https://docs.telethon.dev/en/v2/developing/faq.html)
- [Telethon Issue #3955: Account bans](https://github.com/LonamiWebs/Telethon/issues/3955)
- [Stack Overflow: Telethon rate limits](https://stackoverflow.com/questions/76198570)
- [Telebrief: Multi-channel digest tool](https://github.com/belaytzev/Telebrief)
- [tg-channel-digest: Real-time monitoring](https://github.com/Lonky1995/tg-channel-digest)
