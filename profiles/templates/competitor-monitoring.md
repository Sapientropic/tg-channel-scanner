# Profile: Competitor Monitoring

## Basic Info
- **Focus**: Competitor launches, pricing changes, hiring, partnerships, incidents, and customer signals
- **Audience**: Founder, product marketer, or sales lead
- **Noise exclusions**: Generic brand posts, repeated announcements, and unsubstantiated rumors

## Search Rules
1. Include items that may change positioning, roadmap, sales, or messaging.
2. Preserve the competitor name, event, source, and next action.
3. Rate high when the item needs action within 24 hours.

## Extraction Schema
mode: custom
top_level_key: items
dedup_fields: [competitor, event]
fields:
  - name: source_message_refs
    type: list
  - name: source_message_ids
    type: list
  - name: competitor
    required: true
  - name: event
    required: true
  - name: impact
  - name: recommended_action
  - name: rating
    values: [high, medium, low]
  - name: why
  - name: source

## Extraction Prompt
system_prompt: |
  Extract competitor intelligence that could affect product, sales, positioning,
  hiring, partnerships, or risk monitoring. Keep evidence tied to the source.

## Report Labels
report_title: "Competitor Signal Brief"
section_high: "Act Today"
section_medium: "Investigate"
section_low: "Archive"
stats_label: "Competitor signals"
output_filename: "competitor-signal-brief-{date}.md"
profile_section_title: "Monitoring Profile"
methodology_label: "Telegram competitor sources"
