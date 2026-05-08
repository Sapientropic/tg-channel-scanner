# Profile: Airdrop Watchlist

## Basic Info
- **Focus**: Credible airdrop, quest, testnet, and points opportunities
- **Risk posture**: Avoid wallet-drain, seed phrase, suspicious bridge, and paid-access traps
- **Timing**: Prefer fresh, time-sensitive opportunities

## Search Rules
1. Include actionable opportunities with source evidence and clear next steps.
2. Exclude generic hype, referral spam, and posts that ask for seed phrases.
3. Rate urgency and credibility separately in the reason.

## Extraction Schema
mode: custom
top_level_key: items
dedup_fields: [project, event]
fields:
  - name: source_message_refs
    type: list
  - name: source_message_ids
    type: list
  - name: project
    required: true
  - name: event
    required: true
  - name: deadline
  - name: action
    values: ["Join now", "Review source", "Skip"]
  - name: rating
    values: [high, medium, low]
  - name: why
  - name: risks
    type: list
  - name: source

## Extraction Prompt
system_prompt: |
  Extract credible crypto airdrop, quest, testnet, points, or allowlist signals.
  Reject spam, seed phrase requests, guaranteed-profit claims, and vague hype.

## Report Labels
report_title: "Airdrop Signal Brief"
section_high: "Act Now"
section_medium: "Review Source"
section_low: "Skip Or Archive"
stats_label: "Airdrop signals"
output_filename: "airdrop-signal-brief-{date}.md"
profile_section_title: "Watchlist Profile"
methodology_label: "Telegram crypto channels"
