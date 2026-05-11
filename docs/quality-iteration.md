# Signal Desk Quality Iteration

Current truth for the post-13:00 Signal Desk visual/UX implementation pass. The historical log remains archived at `docs/archive/quality-iteration-20260511-full-log.md`; this file is the current handoff surface only.

## Operating Contract

- Mode: Integrity.
- Scope: Desk `Start / Review / Profiles / Runs / Settings`, desktop through mobile.
- User lens: ordinary app user, ADHD, low tolerance for repeated low-value noise, strong preference for visible decision surfaces.
- Design contracts: `.frontend-design-context.md` and `.impeccable.md`.
- Reviewer gate: KIMI is the devil UX/aesthetic reviewer; at least one non-KIMI reviewer must give an effective pass. Automated audit is evidence, not taste acceptance.
- Current window: the old `2026-05-11 13:00 +08:00` stop condition is historical; this pass reflects the later implementation requested from the live screenshots.

## Current Verdict

Implementation now addresses the user's latest app-only blockers across Start, Review, Profiles, Runs, Settings, feedback learning, AI API setup, and the post-KIMI/Profile/Runs follow-up. Deterministic verification is green. The latest KIMI devil UX review produced P0/P1 items for focus visibility, empty-state tone, reduced-motion, and mobile control hierarchy; those items have been implemented and locally verified. Final taste acceptance remains user-owned.

Verified locally for this slice:
- Screenshot/audit set: `output/quality-review/20260511-2220-profile-create-runs-copy-fix/`.
- Audit covers `Start / Review / Profiles / Runs / Settings` at `1440x1000`, `1360x900`, `1024x768`, `390x844`, and `375x812`.
- No horizontal overflow in all 25 tab/viewport records.
- No detected visible touch target under `44x44`.
- `npm test -- --run`: 12 files / 92 tests passed.
- `npm run build`: passed.
- `python -m pytest -q`: 349 tests and 60 subtests passed.
- Reduced-motion Playwright check: zero animated/transitioning elements under `prefers-reduced-motion: reduce`.
- Keyboard focus smoke: first tab hits `Skip to active board` with visible 2px outline; second focus target also has visible outline.
- Mobile text smoke at `390x844`: Start exposes `Setup`, `AI API`, `Profiles`, `Sources`, `Runs`; Profiles exposes `New profile`; Runs exposes `Repair source list`, `Check setup`, and `Run fresh scan`.
- Expanded mobile Profile editor专项: `421x710`, editor visible, `scrollWidth == clientWidth == 421`, no overflow.
- Mobile Runs repair专项: repair path copy is explicit; no `Fix sources`, no `Test setup`, no `Needs attention` label in product UI.
- Desk health endpoint confirms `desk_ai_settings_v1` capability at `/api/desk/health`.

Reviewer gate status:
- Previous KIMI accept `5f0fb86916a5` and Qwen accept `96c931350533` apply only to the earlier `20260511-1422-final-kimi-fast-follow` packet.
- Qwen plan `c96158af3845` was used for this implementation pass, but it reviewed the pre-fix packet and is not a post-fix acceptance gate.
- Qwen post-fix review `ce04983d3aa7` returned pass-with-risks, flagged repeated failed-scan evidence as P1, and that specific P1 was fixed by collapsing mobile evidence groups.
- Qwen re-review `ad65cdf70795` returned pass-with-risks with all user-reported P0/P1 resolved; remaining risks are P2.
- Gemini attempts failed or timed out, so Gemini is not counted as reviewer evidence.
- KIMI devil review `a88b1d46e5c3` was used for the empty-state/focus/reduced-motion/mobile-control slice. Its P0/P1 items have been fixed; a fresh post-fix KIMI re-review is still optional gate evidence, not yet recorded here.

## Latest User-Driven Fixes

- Start:
  - Ready mode no longer depends on hidden `More controls`.
  - Added visible management shortcuts for `Setup`, `AI API`, `Profiles`, `Sources`, `Runs`, dry-run automation, and manual scan.
  - `Setup` opens the ready-state setup drawer so a user can re-edit or re-run setup instead of falling back to CLI memory.
- AI API:
  - Added Desk-native AI API settings in `Settings > AI API`.
  - Added local provider status cards and save/clear flows for OpenAI, DeepSeek, MiniMax token-plan, and xAI keys.
  - Saved keys go through Windows Credential Manager; environment variables still take precedence.
  - Desk actions, report generation, and OCR resolution now fall back to locally saved AI keys when env vars are absent.
- Review:
  - Removed the giant mobile `More filters` block; filters are compact chips.
  - Backlog preview cards are clickable and jump to the relevant review bucket.
  - When the active `Latest action` filter becomes empty while backlog remains, Desk auto-switches to the next non-empty bucket instead of implying all work is done.
- Runs:
  - The failed-scan health card now includes app-native repair actions: `Repair source list`, `Check setup`, and `Run fresh scan`.
  - `Fix sources` no longer jumps to Settings from the health card; it runs the existing source-import repair action.
  - The health card no longer lists raw failed scan rows. It gives one direct repair path instead.
  - Recent Evidence no longer labels the primary group as vague `Needs attention`; it says `Failed scans to fix` and gives the repair order.
  - Recent Evidence groups are collapsible; mobile defaults them closed so the health repair card is not immediately followed by repeated failed-scan content.
  - Default-off OCR with media is no longer a red/yellow warning. It renders as `OCR optional` with info tone unless OCR was enabled and failed.
- Profiles:
  - Added a collapsible `New profile` entry. Users can paste a plain-language goal or attach Markdown, text, or PDF; Desk parses it and creates a local profile/config after confirmation.
  - Profiles have a visible `Edit profile` entry.
  - Numeric edit fields are legible in desktop and mobile.
  - Each Profile card is now collapsible; mobile defaults to a compact summary so multiple profiles do not crush the first screen.
  - The expanded mobile Profile editor no longer protrudes horizontally.
  - Current matching context is shown before editing, and users can draft plain-language matching-rule changes without raw JSON or CLI.
  - Pending profile changes are labeled `Profile Drafts`; draft title wrapping has been fixed.
- Feedback learning:
  - The primary button is now `Generate drafts`, not a long JSON/export-oriented action.
  - Clicking it calls the Desk API and creates profile draft suggestions; the latest manual smoke created one pending profile draft successfully.
  - JSONL export remains available only as CLI fallback/troubleshooting.

## Latest Evidence

- Reviewer packet: `output/quality-review/20260511-2220-profile-create-runs-copy-fix/reviewer-packet.md` (not yet generated).
- Audit JSON: `output/quality-review/20260511-2220-profile-create-runs-copy-fix/visual-audit.json`.
- Key screenshots:
  - `desktop-start.png`
  - `desktop-review.png`
  - `desktop-profiles.png`
  - `desktop-runs.png`
  - `desktop-settings.png`
  - `mobile-start.png`
  - `mobile-review.png`
  - `mobile-runs-repair.png`
  - `mobile-profiles-expanded-editor.png`
  - `mobile-375-start.png`
  - `mobile-375-runs.png`
  - `mobile-375-profiles.png`
  - `check-desktop-settings-ai.png`
  - `check-desktop-generate-drafts-result.png`
  - `check-desktop-profiles-draft-final.png`

## Residual Risk

- KIMI has not yet re-reviewed the latest 22:20 slice after implementation fixes.
- Mobile `Start` now scrolls vertically after visible shortcuts were added: latest audit shows `390x844` scrollHeight `886`, `375x812` scrollHeight `1107`. This is an intentional tradeoff for discoverability unless reviewer/user escalates density.
- Mobile `Runs` scrolls vertically because repair actions and chart/evidence summaries are visible. No horizontal overflow or small target was detected.
- `desktop-1360` Runs scrolls vertically by 136px because the health chart, repair actions, and evidence rows remain visible. This is currently P2 visual density, not a functional blocker.
- Recent Evidence still exists behind `View` on mobile; if user/reviewer still finds the summary row noisy, the next slice should reduce the group summary text rather than re-expand details.
- The generated feedback-to-profile note is intentionally conservative and text-based; it does not infer deep schema-specific preferences beyond existing profile patch machinery.
- Applying all pending profile drafts is one click but still guarded by existing profile hash checks; stale drafts can fail safely and require review.
- Empty-data states now have direct app actions in Review/Runs/Profiles and warning tone is no longer used for benign empty states, but broader synthetic data permutations remain a follow-up audit.
- Keyboard focus and reduced-motion have smoke coverage, not exhaustive route-by-route focus-order proof.
- Human taste acceptance remains user-owned.

## Next Action

1. Send `output/quality-review/20260511-2220-profile-create-runs-copy-fix/reviewer-packet.md` to KIMI if continuing formal reviewer gate.
2. Fix any new P0/P1, especially if KIMI escalates mobile Start density, Runs chart density, or feedback/profile draft clarity.
