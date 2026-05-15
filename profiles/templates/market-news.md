# Profile: Market And News Watch

## Basic Info
- **Focus**: Market-moving news, policy changes, product launches, incidents, partnerships, and risk events
- **Audience**: Analyst who needs a short decision brief
- **Decision use**: Separate confirmed facts from claims that need verification
- **Noise exclusions**: Routine price chatter, memes, repeated reposts, and unverified rumors

## Search Rules
1. Keep items with concrete event details, named entities, source context, and a plausible decision impact.
2. Rate high when the item can change a decision, watchlist, or investigation today.
3. Rate medium when the item needs verification, source triangulation, or follow-up.
4. Rate low when it is useful background context but not a decision trigger.
5. Preserve source_message_refs, event time hints, original links, affected entities, and negative evidence.

## Rejection Rules
1. Reject routine price chatter, technical-analysis calls, memes, and sentiment-only posts without event evidence.
2. Reject repeated reposts unless they add a new source, timestamp, material detail, or correction.
3. Reject unverifiable rumors, anonymous claims, and screenshots without source context as high or medium matches.
4. Do not match generic brand mentions, token tickers, or market commentary when no concrete event is present.
5. Do not include old news unless the post explains a new impact, deadline, or decision context.

## Prefilter Tuning
- Add entity or event-type keywords when missed high-value items share them.
- Remove broad ticker or sentiment terms when they repeatedly create price-chatter false positives.
- Prefer keywords tied to official announcements, policy actions, outages, launches, filings, and incidents.

## Good Examples
- A regulator announces a policy change with source link, effective date, and affected market segment.
- A company launches a product or partnership that changes competitive positioning or customer behavior.

## Bad Examples
- A channel posts "BTC moon soon" or a chart screenshot without event evidence.
- A rumor thread repeats a claim without source, timestamp, or decision relevance.
- A repost repeats yesterday's launch announcement with no new information.

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
  - name: entities
    type: list
  - name: decision_factors
    type: list
  - name: negative_evidence
  - name: deadline_or_time
  - name: rating
    values: [high, medium, low]
  - name: why
  - name: follow_up
  - name: source
  - name: action
    values: [Act, Review, Skip]

## Extraction Prompt
system_prompt: |
  Extract market or news items that could change a decision, investigation, or
  watchlist. Separate confirmed facts from unverified claims. Keep source refs,
  event time, entities, decision factors, negative evidence, and next follow-up.
  Reject routine price chatter, memes, reposts, and unsupported rumors.

## Report Preferences
- Lead with the items that change a decision today.
- Make verification gaps explicit instead of overstating uncertain claims.
- Keep low-priority items as background only when they clarify a boundary.

## Follow-up Preferences
- Prefer primary-source announcements or posts that link to original evidence.
- Down-rank sentiment-only market chatter unless it is tied to a concrete event.

## Report Labels
report_title: "Market News Signal Brief"
section_high: "Decision-Relevant"
section_medium: "Verify Next"
section_low: "Background"
stats_label: "Signals"
output_filename: "market-news-signal-brief-{date}.md"
profile_section_title: "Market News Monitoring Profile"
methodology_label: "Telegram news channels"
