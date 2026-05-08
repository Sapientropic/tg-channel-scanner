# Profile: Market And News Watch

## Basic Info
- **Focus**: Market-moving news, policy changes, product launches, and risk events
- **Audience**: Analyst who needs a short decision brief
- **Noise exclusions**: Routine price chatter, memes, repeated reposts, and unverified rumors

## Search Rules
1. Keep items with concrete event details and source context.
2. Rate high when the item changes a decision today.
3. Rate medium when it needs verification or follow-up.
4. Rate low when it is background context only.

## Extraction Schema
mode: custom
top_level_key: items
dedup_fields: [topic, event]
fields:
  - name: source_message_refs
    type: list
  - name: source_message_ids
    type: list
  - name: topic
    required: true
  - name: event
    required: true
  - name: market_impact
  - name: urgency
  - name: rating
    values: [high, medium, low]
  - name: why
  - name: follow_up
  - name: source

## Extraction Prompt
system_prompt: |
  Extract market or news items that could change a decision, investigation,
  or watchlist. Separate confirmed facts from unverified claims.

## Report Labels
report_title: "Market News Signal Brief"
section_high: "Decision-Relevant"
section_medium: "Verify Next"
section_low: "Background"
stats_label: "Signals"
output_filename: "market-news-signal-brief-{date}.md"
profile_section_title: "Monitoring Profile"
methodology_label: "Telegram news channels"
