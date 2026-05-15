# Profile: Research Leads

## Basic Info
- **Focus**: Papers, datasets, tools, funding calls, events, expert leads, and reproducible findings
- **Audience**: Researcher who needs evidence and follow-up paths
- **Evidence posture**: Prefer primary source links, named authors, datasets, repo links, and concrete methodology
- **Noise exclusions**: Generic thought leadership, reposts without source, and unverifiable claims

## Search Rules
1. Include leads with enough evidence, provenance, and detail to investigate later.
2. Preserve source_message_refs, original links, authors, institutions, dataset names, and follow-up actions.
3. Rate high when the lead deserves action today because of novelty, deadline, or strategic relevance.
4. Rate medium when it is promising but needs validation, replication, or source follow-up.
5. Keep low only when the item teaches a useful boundary or archive context.

## Rejection Rules
1. Reject generic thought leadership, motivational posts, and commentary that does not link to evidence.
2. Reject unverifiable claims, vague "breakthrough" language, and reposts that omit the original paper, dataset, or source.
3. Reject tool announcements without docs, repo, demo, benchmark, or credible author/source context.
4. Do not match broad research chatter unless it provides a concrete lead, evidence artifact, or follow-up path.
5. Do not include stale conference reminders unless there is a new deadline, call, program, or registration action.

## Prefilter Tuning
- Add author, institution, benchmark, dataset, or venue names when missed good leads repeat them.
- Remove broad words like "AI" or "research" when they pull generic commentary.
- Prefer terms tied to artifacts: paper, dataset, benchmark, repo, grant, CFP, workshop, replication, release.

## Good Examples
- A lab announces a paper with PDF, dataset, benchmark, authors, and a claim worth validating.
- A funding call or workshop deadline includes topic scope, deadline, eligibility, and official link.

## Bad Examples
- A repost says "huge AI breakthrough" without paper, source, method, or author.
- A generic opinion thread discusses a field trend but offers no artifact or follow-up path.
- A tool launch has no repository, docs, demo, benchmark, or credible source refs.

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
  - name: artifact_link
  - name: deadline
  - name: authors_or_org
  - name: follow_up
  - name: rating
    values: [high, medium, low]
  - name: why
  - name: action
    values: [Follow up today, Save and verify, Archive]

## Extraction Prompt
system_prompt: |
  Extract research leads with concrete evidence, provenance, and next actions.
  Preserve source refs, original links, authors or organizations, deadlines,
  and evidence artifacts. Do not inflate weak mentions into findings. Reject
  generic thought leadership, unsupported breakthrough claims, and reposts
  without primary-source context.

## Report Preferences
- Put time-sensitive or high-novelty leads first.
- State what evidence exists and what still needs verification.
- Keep low-priority leads only when they help define future matching boundaries.

## Follow-up Preferences
- Prefer primary-source research artifacts over commentary about those artifacts.
- Down-rank broad opinion threads unless they include a concrete paper, dataset, tool, or deadline.

## Report Labels
report_title: "Research Lead Brief"
section_high: "Follow Up Today"
section_medium: "Save And Verify"
section_low: "Archive"
stats_label: "Research leads"
output_filename: "research-lead-brief-{date}.md"
profile_section_title: "Research Profile"
methodology_label: "Telegram research sources"
