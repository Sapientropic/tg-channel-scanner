# Profile: Frontend Developer Opportunity Leads

## Basic Info
- **Role**: Frontend-focused developer opportunities worth acting on
- **Level**: Middle to senior, or specialist contract work with clear budget
- **Work format**: Remote, clearly relocation-friendly, contract, freelance, or Mini Apps / TON project work
- **Location exclusions**: On-site only roles in rejected locations

## Search Rules
1. Include roles, contract projects, freelance gigs, and Mini Apps / TON work that match the target stack, seniority, and work format.
2. First classify whether the source is an employer, recruiter, client, or project owner offering paid work.
3. Candidate CVs, resumes, portfolio posts, "looking for work" posts, and self-promotion are not vacancies; never rate them high or medium.
4. Backend-only and full-stack generalist roles are off-profile unless they are explicitly frontend-heavy.
5. Rate real openings as high, medium, or low.
6. Keep low-priority items only when they explain a useful boundary.
7. Preserve contact handles, emails, application links, budget, and payment clues.
8. For fast alerts, rate high only when the role is worth acting on within the next hour.
9. Treat keyword prefilter hits as candidates only; the final rating must still be based on fit, freshness, and actionability.

## Rejection Rules
1. Reject candidate CVs, resumes, portfolio posts, "looking for work" posts, and self-promotion because they are not an employer/recruiter/client opening.
2. Reject backend-only and generic full-stack roles unless the post explicitly says the work is frontend-focused.
3. Reject unpaid internships, course ads, job-board navigation posts, repeated channel promo text, and vague hiring rumors.
4. Do not match roles that are on-site only in rejected locations, or posts without a real contact, application, budget, or client/employer signal.
5. Do not include low-confidence guesses as high or medium; keep only useful boundary examples as low.

## Prefilter Tuning
- Suggest adding keywords when missed good roles share a repeated phrase.
- Suggest removing keywords when they repeatedly create false positives.
- Prefer phrases that imply an actual opening, not generic stack terms alone.

## Good Examples
- A founder asks for a paid React/TypeScript contractor for a Telegram Mini App and includes budget, deadline, and contact.
- A recruiter posts a remote frontend-heavy senior role with stack, company, compensation hint, and application link.

## Bad Examples
- A developer posts a candidate CV, portfolio, or "looking for work" message.
- A backend-only or generic full-stack vacancy has no clear frontend ownership.
- A channel reposts a job-board list without employer, budget, contact, or source refs.

## Extraction Schema
mode: custom
top_level_key: items
dedup_fields: [company, role]
fields:
  - name: source_message_refs
    type: list
  - name: source_message_ids
    type: list
  - name: opportunity_type
    values: [job, contract, freelance_gig, mini_app_ton_project, candidate_profile, non_vacancy, other]
  - name: company
  - name: role
    required: true
  - name: location
  - name: salary
  - name: budget
  - name: contact
  - name: apply_url
  - name: deadline
  - name: posted_at_hint
  - name: urgency_reason
  - name: rating
    values: [high, medium, low]
  - name: why
  - name: action
    values: [Apply, Inspect, Skip unless criteria change]

## Extraction Prompt
system_prompt: |
  Extract only real frontend-focused developer opportunities: job openings,
  contract roles, freelance gigs, paid Mini Apps / TON projects, or clearly
  actionable hiring leads. Prefer a compact item over a verbose explanation.
  Return at most 8 items, ranked by near-term actionability and profile fit.
  If a digest contains many opportunities, extract only the top 3 matching
  items from that digest.
  Return no item for generic career discussion, job-board navigation, course
  ads, repeated channel promo text, low-confidence guesses, unpaid vague ideas,
  candidate CV/resume/portfolio/self-promotion posts, "looking for work" posts,
  backend-only roles, full-stack generalist roles without a clear frontend-heavy
  scope, or roles that are clearly off-profile. If a non-vacancy boundary
  example is useful, keep it low only with action "Skip unless criteria change"
  and say why it is not an employer/recruiter/client opening. Do not copy full
  job descriptions; keep why, action, and urgency_reason to one short sentence
  each.

## Report Preferences
- Explain why high-priority leads deserve action today.
- Put urgent high-priority opportunities first and explain the fastest safe next step.
- For medium matches, state what must be verified before applying.
- For low matches, state which criterion would need to change.

## Report Labels
report_title: "Frontend Opportunity Signal Report"
section_high: "Apply Today"
section_medium: "Inspect First"
section_low: "Boundary Examples"
stats_label: "Frontend opportunities"
output_filename: "job-signal-report-{date}.md"
profile_section_title: "Frontend Opportunity Profile"
methodology_label: "Telegram opportunity channels"


## Follow-up Preferences
- Prefer frontend-heavy roles over generic full-stack work.
- Skip backend-only roles unless the source explicitly describes a frontend scope.
- Skip lead-only roles unless they still include hands-on frontend work.
