# Profile: Competitor Monitoring

## Basic Info
- **Focus**: Competitor launches, pricing changes, hiring, partnerships, incidents, customer signals, and positioning shifts
- **Audience**: Founder, product marketer, sales lead, or strategy operator
- **Business use**: Highlight signals that may change roadmap, messaging, sales, hiring, or risk monitoring
- **Noise exclusions**: Generic brand posts, repeated announcements, and unsubstantiated rumors

## Search Rules
1. Include items that may change positioning, roadmap, sales, messaging, hiring, partnerships, or risk response.
2. Preserve source_message_refs, competitor name, event, evidence, source, and recommended next action.
3. Rate high when the item needs action within 24 hours or changes an active decision.
4. Rate medium when the item is useful but needs confirmation, customer validation, or team routing.
5. Keep low only when it documents a boundary, minor background signal, or archive-worthy weak evidence.

## Rejection Rules
1. Reject generic brand mentions, evergreen marketing copy, and repeated launch blurbs without new information.
2. Reject unsubstantiated rumors, anonymous claims, and customer anecdotes without enough context to verify.
3. Reject broad industry news that does not name a competitor, adjacent product, or actionable comparison point.
4. Do not match social vanity metrics, meme posts, or community chatter unless they reveal a concrete customer or product signal.
5. Do not include stale announcements unless the post adds a new price, feature, partnership, incident, or customer reaction.

## Prefilter Tuning
- Add competitor names, product names, pricing-page terms, launch phrases, incident terms, and customer complaint patterns.
- Remove broad category keywords when they repeatedly pull generic industry commentary.
- Prefer source phrases that imply evidence: changelog, pricing, launch, outage, integration, hiring, complaint, migration.

## Good Examples
- A competitor launches a new feature with screenshots, changelog link, and a positioning claim.
- A customer complaint thread names a competitor, problem, use case, and buying risk.
- A pricing-page update changes packaging, limits, or enterprise terms.

## Bad Examples
- A generic brand mention says a competitor is "great" without product, customer, or business evidence.
- A rumor claims a competitor is raising money but has no source, date, or impact.
- A repost repeats an old launch announcement without new feature, price, customer, or incident detail.

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
  - name: signal_type
    values: [launch, pricing, hiring, partnership, incident, customer_signal, positioning, other]
  - name: impact
  - name: evidence
  - name: recommended_action
  - name: rating
    values: [high, medium, low]
  - name: why
  - name: source
  - name: action
    values: [Act today, Investigate, Archive]

## Extraction Prompt
system_prompt: |
  Extract competitor intelligence that could affect product, sales, positioning,
  hiring, partnerships, incidents, or risk monitoring. Keep evidence tied to
  source refs and avoid turning generic brand mentions into signals. Reject
  repeated announcements, unsupported rumors, social vanity metrics, and broad
  industry news without competitor-specific actionability.

## Report Preferences
- Lead with signals that should change a decision within 24 hours.
- State the business function most likely to act: product, sales, marketing, hiring, or support.
- For medium matches, name the verification or routing step.

## Follow-up Preferences
- Prefer product, pricing, customer, and incident evidence over generic awareness mentions.
- Down-rank repeated launch copy unless a new customer, pricing, or roadmap detail appears.

## Report Labels
report_title: "Competitor Signal Brief"
section_high: "Act Today"
section_medium: "Investigate"
section_low: "Archive"
stats_label: "Competitor signals"
output_filename: "competitor-signal-brief-{date}.md"
profile_section_title: "Competitor Monitoring Profile"
methodology_label: "Telegram competitor sources"
