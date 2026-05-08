# Profile: Research Leads

## Basic Info
- **Focus**: Papers, datasets, tools, funding calls, events, and expert leads
- **Audience**: Researcher who needs evidence and follow-up paths
- **Noise exclusions**: Generic thought leadership, reposts without source, and unverifiable claims

## Search Rules
1. Include leads with enough detail to investigate later.
2. Preserve source identity and any original links.
3. Rate high when the lead deserves action today.

## Extraction Schema
mode: custom
top_level_key: items
dedup_fields: [lead, source]
fields:
  - name: source_message_refs
    type: list
  - name: source_message_ids
    type: list
  - name: lead
    required: true
  - name: source
    required: true
  - name: domain
  - name: evidence
  - name: follow_up
  - name: rating
    values: [high, medium, low]
  - name: why

## Extraction Prompt
system_prompt: |
  Extract research leads with concrete evidence, provenance, and next actions.
  Do not inflate weak mentions into findings.

## Report Labels
report_title: "Research Lead Brief"
section_high: "Follow Up Today"
section_medium: "Save And Verify"
section_low: "Archive"
stats_label: "Research leads"
output_filename: "research-lead-brief-{date}.md"
profile_section_title: "Research Profile"
methodology_label: "Telegram research sources"
