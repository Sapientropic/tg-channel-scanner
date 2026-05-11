# Signal Desk UX Redesign — Devil Review

> Target: app users, no CLI knowledge, ADHD, visual-first.  
> Goal: setup / scan / review / profile tuning / run repair, all from the Desk.  
> Tone: no praise, only what's broken and how to fix it.

---

## P0 — Fix before anything else

| # | Pain | Why P0 |
|---|------|--------|
| 1 | Profile Draft meta is CLI debris (`Profiles/jobs.md`, `base 4a3b9c2`, `+4/-0`) | User sees git output, not product UI. Blocks trust in "Apply" button. |
| 2 | Raw diff in draft expand is unreadable | Unified diff (`@@ -12,5 +12,7 @@`) means nothing to non-devs. Zero value, high cognitive load. |
| 3 | Runs health chart is ugly and the `36% complete` number is nonsense | Visual priority user hits this on every load. It looks broken. |
| 4 | Failed scan CTA is "Test setup" / "Fix sources" — vague abstractions | User doesn't know what "Test setup" does. Needs a verb that fixes the actual failure. |

## P1 — Structural improvements

| # | Pain | Why P1 |
|---|------|--------|
| 5 | Feedback tuning dumps card titles into prompt instead of extracting preferences | Titles are noise; user wants to know *what Desk learned*, not *which cards*. |
| 6 | Profiles show only `2h / 20 messages`, never the actual match rules / background / exclusions | User can't see *why* matches happen. Can't tune without opening raw markdown. |
| 7 | No "Learning" surface explaining the feedback loop | ADHD user needs clear cause→effect: "I did X → Desk learned Y → next scan will Z". |

---

## 1. Profile Drafts — New Layout & Copy

### Current (broken)
```
[ Jobs Fast                    ] [pending]
Profiles/jobs.md  05-11 15:51  +4/-0  base 4a3b9c2
Learns from your Review choices
Desk feedback tuning: prefer matches like Senior Frontend...
[View draft diff]  [Apply to profile]
```

### Redesigned
```
┌─────────────────────────────────────────────┐
│ 🟡 Pending · Jobs Fast                      │  ← tone chip + profile name only
│                                             │
│  Learning from your Review choices          │  ← human-readable source label
│  Based on 12 keep / 3 skip / 2 wrong        │  ← feedback stats (new field)
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │ Will be added to "Match rules"      │    │  ← section context
│  │ • Prefer senior IC roles            │    │  ← extracted preference (NOT raw title)
│  │ • De-prioritize agency recruiters   │    │
│  │ • Avoid crypto/blockchain listings  │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  [✓ Apply to profile]  [Raw diff]           │  ← primary + secondary
└─────────────────────────────────────────────┘
```

### Copy rules
- **Never show**: file paths, hashes, diff stats, `@@` lines, `---/+++` headers.
- **Always show**: which profile, what kind of change (Learning vs Manual note), how many feedback events fed it.
- **CTA hierarchy**: `Apply to profile` (primary) > `Raw diff` (tiny tertiary, hidden by default).

### Data/API changes needed
- `ProfilePatch` schema add:
  - `feedback_stats?: { keep: number; skip: number; false_positive: number }`
  - `extracted_preferences?: string[]`  ← **new backend NLP step** (see Slice 4)
  - `section_target?: "match_rules" | "background" | "exclusions"`  ← from `_append_follow_up_rule` context
- `PATCH /api/profile-patches/{id}/user-summary` (optional) if we want to let users edit the extracted summary before apply.

---

## 2. Profiles Tab — New Layout & Copy

### Current (broken)
```
Jobs Fast    [Monitoring]
24h history · 20 messages · All topics · 1 notification
[Pause] [Day/All/Mute] [Edit profile]
```

What the user actually needs to see:
- What is this profile looking for?
- What does it ignore?
- What have I taught it?

### Redesigned
```
┌──────────────────────────────────────────────────────────┐
│ 🟢 Jobs Fast                              [Monitoring ▼] │
│                                                          │
│  SCAN SETTINGS         MATCH LOGIC        ALERTS         │
│  ├─ Look back: 24h     ├─ Background:     ├─ Day only    │
│  ├─ Max messages: 20   │  Remote-first    └─ 1 target    │
│  └─ Sources: jobs      │  Senior IC roles                │
│                        ├─ Prefer:                         │
│                        │  • Senior roles                  │
│                        │  • React/TypeScript              │
│                        ├─ Avoid:                          │
│                        │  • Agency recruiters             │
│                        │  • Unpaid internships            │
│                        └─ Exclusions:                     │
│                           • Crypto/blockchain             │
│                                                           │
│  [Edit match logic]  [Pause monitoring]                   │
└──────────────────────────────────────────────────────────┘
```

### Copy rules
- Replace `Scan history` / `Messages` / `Item limit` with plain labels: `Look back`, `Max messages`.
- **New sections** (must be visible, not hidden behind edit):
  - `Background` — what the profile is fundamentally about.
  - `Prefer` / `Avoid` — extracted from `## Follow-up Preferences`.
  - `Exclusions` — extracted from `## Exclusions` or negative bullets.
- If a section is empty, show a muted placeholder: `"No avoid rules yet — Desk will learn from your skips."`

### Edit flow
- Clicking `Edit match logic` expands an inline panel (not modal).
- Each section becomes a `<textarea>` with bullet-per-line editing.
- Saving creates a `ProfilePatch` (same flow as today), but the preview is the human-readable card from §1, not raw diff.

### Data/API changes needed
- `GET /api/profiles/{id}/content` — return parsed profile sections:
  ```json
  {
    "background": "Remote-first senior IC roles...",
    "preferences": ["Senior roles", "React/TypeScript"],
    "avoid_rules": ["Agency recruiters", "Unpaid internships"],
    "exclusions": ["Crypto/blockchain"],
    "follow_up_count": 4
  }
  ```
- OR extend `GET /api/state` `Profile` object with `content_summary` field.
- `POST /api/profiles/{id}/sections` — accept structured edits to background/prefer/avoid/exclusions, generate the patch internally.

---

## 3. Learning Surface — New Layout & Copy

### Current (broken)
Feedback tuning exists only as a generated patch. There is no place that says "Desk is learning."

### Redesigned — Add a "Learning" tab (or section inside Profiles)
```
┌──────────────────────────────────────────────────────────┐
│ 🧠 Learning                                               │
│                                                           │
│  What Desk has learned from your reviews                  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Jobs Fast                                           │  │
│  │ • Prefers senior roles (from 12 keep choices)       │  │
│  │ • Avoids agency recruiters (from 3 skips)           │  │
│  │ • Avoids crypto listings (from 2 false positives)   │  │
│  │                                                     │  │
│  │ [Review draft]  [Clear learning]                    │  │
│  └─────────────────────────────────────────────────────┘  │
│                                                           │
│  How it works                                             │
│  1. You review cards (keep / skip / wrong)               │
│  2. Desk extracts patterns from your choices             │
│  3. You approve the draft → future scans use it          │
│                                                           │
│  [Generate now]  —  Last generated: 2 hours ago          │
└──────────────────────────────────────────────────────────┘
```

### Copy rules
- Use causal chain: `You did X → Desk did Y → Result is Z`.
- Numbers create trust: "from 12 keep choices" not "learned from some cards".
- `Clear learning` is a destructive action with confirmation; it resets the feedback state for that profile.

### Data/API changes needed
- `GET /api/learning` (or embed in state):
  ```json
  {
    "profiles": [
      {
        "profile_id": "jobs",
        "extracted_preferences": [
          { "text": "Prefers senior roles", "source": "keep", "count": 12 },
          { "text": "Avoids agency recruiters", "source": "skip", "count": 3 }
        ],
        "pending_patch_id": "patch_abc",
        "last_generated_at": "2026-05-11T14:00:00Z"
      }
    ]
  }
  ```
- `POST /api/learning/{profile_id}/clear` — remove feedback-derived patches and reset counters.

---

## 4. Runs — New Layout & Copy

### Current (broken)
- `36%` giant number — what is this? Completion rate of what? User doesn't care.
- 7-day bar chart with gradient bars inside gradient bars — busy, illegible on mobile.
- `Fix failed scans` → buttons say `Test setup` and `Fix sources`. Test setup runs `doctor_jobs`, which is opaque.

### Redesigned — Health header
```
┌──────────────────────────────────────────────────────────────┐
│ THIS WEEK                          [Run repair ▼]           │
│                                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐   │
│  │  14      │  │  2       │  │  6       │  │  1         │   │
│  │  scans   │  │  failed  │  │  cards   │  │  in progress│   │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘   │
│                                                               │
│  M  T  W  T  F  S  S                                         │
│  🟢  🟢  🟢  🔴  🟢  🟡  ⚪                                  │
│   ok ok ok fail ok running none                              │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ ⚠️ Last scan failed: "Source access failed"              │  │
│  │    Channel @remotejobshq could not be reached.           │  │
│  │                                                         │  │
│  │    [Run repair]  [Check source]  [Skip for now]         │  │
│  └─────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Copy rules
- Kill the `36% complete` metric. Replace with absolute counts.
- Day dots: `🟢 ok` / `🔴 fail` / `🟡 running` / `⚪ none`. Color only, no bar-height math.
- Failure card:
  - Headline: `Last scan failed: "{diagnosticLabel}"`
  - Detail: specific channel / reason if known.
  - CTA hierarchy:
    1. `Run repair` — runs `doctor_jobs` or targeted retry (new action).
    2. `Check source` — deep-link to Settings > Sources with failing channel highlighted.
    3. `Skip for now` — dismisses the failure banner for this session.

### Data/API changes needed
- `Run` type already has `quality.top_diagnostic_code`. Frontend just needs to surface it better.
- New desk action: `repair_run` or `retry_failed` that targets the latest failed run specifically.
- Optional: `GET /api/runs/{id}/failure-detail` to get channel-level failure reasons.

---

## 5. Slice-by-Slice Implementation Order

### Slice A: Profile Draft UI Cleanup (Frontend only, 1–2 days)
1. In `profiles.tsx`, remove `patch-context-row` metadata (path, hash, diff stat).
2. Replace `<details><pre>{diff_text}</pre></details>` with a human-readable preview card.
3. Style: green left-border for additions, show the `note` text as a bullet list (strip markdown).
4. Update copy: `Apply to profile` primary, `Raw diff` as tiny tertiary link.

**Files**: `profiles.tsx`, `profiles.css`, `display.ts` (for new formatting helpers).

### Slice B: Runs Health Redesign (Frontend only, 1–2 days)
1. Replace `RunHealthChart` big-number + bar-chart with KPI row + day-dot timeline.
2. Add conditional failure banner with `Run repair` / `Check source` / `Skip` CTAs.
3. Wire `Run repair` to existing `doctor_jobs` action (or new action if backend ready).

**Files**: `runs.tsx`, `runs.css`, `projections.ts`.

### Slice C: Profile Content Visibility (Backend + Frontend, 3–4 days)
1. **Backend**: `scripts/profile_schema.py` add parser for:
   - `## Background` or first paragraph → `background`
   - `## Follow-up Preferences` bullets → `preferences`
   - `## Exclusions` or negative bullets → `exclusions`
2. **Backend**: `dashboard_profile_projection` include `content_summary`.
3. **Backend**: New endpoint `GET /api/profiles/{id}/content`.
4. **Frontend**: `ProfilesView` render `background` / `prefer` / `avoid` / `exclusions` as read-only sections.
5. **Frontend**: Expand `ProfileRuntimeSettingsControl` into `ProfileEditor` with section textareas.

**Files**: `profile_schema.py`, `monitor_state.py`, `dashboard_server.py`, `types.ts`, `profiles.tsx`, `profiles.css`, `api/client.ts`.

### Slice D: Learning Surface (Backend + Frontend, 3–4 days)
1. **Backend**: `monitor_state.py` `_feedback_profile_suggestion_note` refactor:
   - Keep title extraction for patch generation.
   - Add `extracted_preferences` array with `text`, `source`, `count`.
   - Store in new `profile_learning_state` table or embed in patch row.
2. **Backend**: New endpoint `GET /api/learning`.
3. **Frontend**: New tab or section rendering learning cards per profile.
4. **Frontend**: Add "How it works" explainer with 3-step causal chain.

**Files**: `monitor_state.py`, `dashboard_server.py`, `types.ts`, `main.tsx` (tab shell), new component `learning.tsx`.

### Slice E: Profile Content Editing (Backend + Frontend, 2–3 days)
1. **Backend**: `POST /api/profiles/{id}/sections` accepts structured edits.
2. **Backend**: Reconstruct markdown from sections, generate patch via existing `create_profile_patch_suggestion`.
3. **Frontend**: Wire section textareas to new API.

**Files**: `dashboard_server.py`, `monitor_state.py`, `profiles.tsx`, `api/client.ts`.

---

## Summary Table

| Slice | Scope | P0/P1 | Backend? | Frontend? | Est. |
|-------|-------|-------|----------|-----------|------|
| A — Draft UI cleanup | Profile Drafts | P0 | No | Yes | 1–2d |
| B — Runs health redesign | Runs | P0 | No* | Yes | 1–2d |
| C — Profile content visibility | Profiles | P1 | Yes | Yes | 3–4d |
| D — Learning surface | Learning | P1 | Yes | Yes | 3–4d |
| E — Profile content editing | Profiles | P1 | Yes | Yes | 2–3d |

*Slice B can use existing `doctor_jobs` action; new `repair_run` action is optional enhancement.

---

## Design Principles (enforced across all slices)

1. **No CLI debris**: paths, hashes, diff syntax, command names stay in Settings > Advanced only.
2. **Causal clarity**: every learning or tuning state must answer "Because you did X, Desk will do Y."
3. **ADHD rhythm**: max 3 sections per card, max 2 CTAs per decision, whitespace > density.
4. **Visual priority over numbers**: status dots > bar charts, bullet lists > tables, color coding > percentages.
5. **Progressive disclosure**: raw diff / raw data always available, always hidden behind a tiny secondary link.
