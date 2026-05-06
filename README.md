# TG Channel Scanner

Read Telegram channel messages on schedule, filter by keywords/profiles, and generate AI-powered digests.

Designed for job seekers monitoring multiple Telegram job channels, but works for any channel monitoring use case.

[**中文文档**](README.zh-CN.md)

---

## Quick Start

### Prerequisites

- Python 3.12+
- Telegram account (phone number)
- Telegram API credentials (`api_id` + `api_hash`)

### Install

```bash
git clone https://github.com/Sapientropic/tg-channel-scanner.git
cd tg-channel-scanner
./setup.sh
```

### Configure

```bash
# 1. Copy config template and fill in your credentials
cp config.example.toml config.toml
# Edit config.toml with your api_id and api_hash

# 2. Login to Telegram
tg auth login
```

### Run a scan

```bash
# Scan all channels in a list, past 24 hours
./scripts/scan.sh channel_lists/example.txt

# Scan past 7 days
./scripts/scan.sh channel_lists/example.txt 7

# Output goes to output/scan_YYYYMMDD_HHMM.jsonl
```

### Summarize with AI

```bash
# Option 1: DeepSeek CLI
deepseek exec --auto "Read file output/scan_XXXX.jsonl, summarize job matches for this candidate profile: $(cat profiles/example.md)"

# Option 2: Feed output directly to Codex / Claude / any AI agent
# Just point your agent at the output/ files and the profile

# Option 3: Python script (OpenAI-compatible API)
python scripts/summarize.py --input output/scan_XXXX.jsonl --profile profiles/example.md
```

---

## How It Works

```
Telegram Channels
  → tgcli reads messages (JSONL)
    → saved to output/
      → AI agent filters + summarizes
        → structured report
```

1. **Read**: `tgcli` (Telethon-based CLI) reads messages from channels you've subscribed to
2. **Filter**: Messages saved as JSONL with date, sender, text, channel info
3. **Summarize**: Your preferred LLM generates a filtered, deduplicated report

## Directory Structure

```
tg-channel-scanner/
├── config.toml              # Your credentials (gitignored)
├── config.example.toml      # Template
├── setup.sh                 # One-command installer
├── profiles/                # Candidate/filter profiles
│   └── example.md           # Example: Frontend Developer job search
├── channel_lists/           # Channel name lists (one per line)
│   └── example.txt          # Example: Russian IT job channels
├── scripts/
│   ├── scan.sh              # Batch channel reader
│   └── summarize.py         # Optional LLM summarizer
├── output/                  # Scan results (gitignored)
└── docs/
    ├── tos-risk-analysis.md
    └── getting-api-credentials.md
```

## Creating Your Own Profile

Copy `profiles/example.md` and edit the matching criteria. The profile tells the AI what to filter for:

```markdown
## Candidate
- Name: Your Name
- Role: Target Role
- Stack: React, TypeScript, ...
- Level: Middle/Senior
- Location: Remote preferred

## Filter Rules
- Only include jobs from last 24 hours
- Remove duplicates (same company + title)
- Exclude: Backend-only, Mobile, DevOps...
```

## Creating Your Own Channel List

Create a `.txt` file in `channel_lists/`, one channel name per line:

```
React Job | JavaScript | Вакансии
Frontend | Удаленка
TypeScript Job Offers
```

Lines starting with `#` are comments.

## Safety & Telegram ToS

This tool reads messages from channels you've already subscribed to — equivalent to scrolling through them manually.

**Important limits:**
- Scan frequency: **max once per day** for automated runs
- Manual/on-demand scans: no limit
- Single channel: **max 100 messages** per read
- Total channels per scan: **max 25**

See [docs/tos-risk-analysis.md](docs/tos-risk-analysis.md) for full analysis.

## Windows

```bat
setup.bat
scripts\scan.bat channel_lists\example.txt
```

## License

MIT
