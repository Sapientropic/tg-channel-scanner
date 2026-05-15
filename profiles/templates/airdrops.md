# Profile: Airdrop Watchlist

## Basic Info
- **Focus**: Credible airdrop, quest, testnet, points, grant, bounty, and allowlist opportunities
- **Audience**: Crypto user who wants actionable opportunities without unsafe wallet behavior
- **Risk posture**: Avoid wallet-drain, seed phrase, suspicious bridge, paid-access, and referral-spam traps
- **Timing**: Prefer fresh, time-sensitive opportunities with clear eligibility and source refs

## Search Rules
1. Include opportunities with official or high-quality source evidence, clear eligibility, and concrete next steps.
2. Prefer posts that name the project, chain, campaign, deadline, reward type, and safe participation path.
3. Rate high only when the opportunity is fresh, credible, and worth acting on today.
4. Rate medium when source verification or wallet-risk review is still needed.
5. Preserve source_message_refs, official links, deadlines, and risk notes so the user can verify before acting.

## Rejection Rules
1. Reject seed phrase requests, wallet-drain prompts, suspicious bridge instructions, fake support, and required private-key actions.
2. Reject guaranteed-profit claims, paid-access alpha groups, pure referral spam, and posts that hide the original source.
3. Reject generic token hype, price chatter, meme threads, and "airdrop soon" rumors without a concrete action.
4. Do not match duplicate campaign reminders unless they add a new deadline, eligibility change, or official update.
5. Do not include opportunities that require unsafe signing or unverifiable downloads.

## Prefilter Tuning
- Add project or campaign keywords only when missed good opportunities repeat that phrase.
- Remove broad tokens such as "airdrop" or "points" when they repeatedly pull referral spam.
- Prefer official campaign names, quest platforms, testnet names, ecosystem names, and deadline wording.

## Good Examples
- An official project channel announces a testnet quest with eligibility, deadline, reward hint, and documentation link.
- A credible ecosystem account summarizes a points campaign and links to the original campaign page.

## Bad Examples
- A post asks users to import a seed phrase, sign an unknown transaction, or download a wallet helper.
- A referral-only post promises guaranteed profit but provides no official source.
- A price-call thread says an airdrop is "confirmed soon" without action, deadline, or provenance.

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
  - name: chain
  - name: deadline
  - name: eligibility
  - name: official_link
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
  Extract credible crypto airdrop, quest, testnet, points, grant, bounty, or
  allowlist signals only when the post contains enough evidence to verify and
  act safely. Keep source refs, official links, deadlines, eligibility, and risk
  notes. Reject spam, seed phrase requests, unsafe signing, guaranteed-profit
  claims, generic hype, and unverifiable rumors.

## Report Preferences
- Put urgent official opportunities first and include the fastest safe verification step.
- For medium matches, state exactly what source or wallet-risk check is still needed.
- For low matches, explain why the opportunity is a boundary example rather than an action item.

## Follow-up Preferences
- Prefer official sources or credible ecosystem summaries over referral-only posts.
- Down-rank quests that require broad wallet permissions until the source is verified.

## Report Labels
report_title: "Airdrop Signal Brief"
section_high: "Act Now"
section_medium: "Review Source"
section_low: "Skip Or Archive"
stats_label: "Airdrop signals"
output_filename: "airdrop-signal-brief-{date}.md"
profile_section_title: "Airdrop Watchlist Profile"
methodology_label: "Telegram crypto channels"
