# Source Discovery And Learning Iteration Notes

Date: 2026-05-17

## Conclusion

The current product target moved from only landing the Telegram Mini App to
hardening the source-discovery and profile-learning loops around it. Public
Telegram discovery stays metadata-only source intake; matching and learning
remain profile-first and local-review driven.

## Implemented Changes

- Fixed the Mini App review filter strip so the selected filter no longer grows
  or changes layout height on tap.
- Restored the Settings source setup path for pasted public Telegram links,
  handles, and starter recommendations alongside opt-in AI folder/all-channel
  discovery.
- Exposed Telegram folder ID in Settings source discovery so users with
  duplicate folder names can target the same backend `folder_id` path already
  supported by the source assistant.
- Replaced the empty packaged `jobs` starter with a small metadata-only
  public-channel recommendation set so `Starter recommendations` is no longer a
  0-source placeholder install.
- Added metadata-only `public_source_candidates_v1` JSON intake to the same
  public-source Preview/Add path, with a guard that rejects candidate payloads
  containing Telegram message/post/raw text.
- Candidate JSON now preserves safe title, language, and recommendation notes
  into the source registry so recommended channels stay reviewable after import.
- Saved Sources now projects and displays that metadata, and source search can
  match recommendation notes as well as handle/topic text.
- Saved Sources now summarizes public recommendation notes into user-facing
  recommendation, noise, and scope text instead of exposing raw probe fields in
  the row body.
- The packaged starter now prefers `channel_lists/jobs.public-candidates.json`
  and keeps `channel_lists/jobs.txt` as a handle-only CLI/fallback mirror.
- Starter import now prunes existing `example_*` placeholder rows before adding
  real public recommendations, so old preview/demo registries repair in place.
- Kept Bot Gateway identity repair from overwriting an installed Mini App menu
  button by default when the dashboard repairs bot identity.
- Allowed newer Review feedback batches to create a new profile-learning draft
  even when an older learning draft was already applied.
- Expanded Profile Coach context so keep, skip, false-positive, and follow-up
  decisions can all shape future matching suggestions.
- Exposed Profile Coach confidence and whether suggestions came from the smart
  LLM path or the local fallback path.
- Surfaced Profile Coach source follow-up suggestions so repeated wrong matches
  can lead users to review noisy sources instead of only tightening profile
  rules.
- Profile draft cards now explain why a draft exists, including the number of
  Review decisions and representative card titles that generated it.
- Settings Learning now shows the full feedback loop explicitly: Review choices,
  Create draft, Apply draft, Run again, and Calibrate, with counts from existing
  feedback and calibration state.
- Mini App cards now carry the same ordinary-user trust cues as Desk review
  cards: a safe original-text excerpt and labeled Telegram jump links instead of
  visible bare URLs, with accessible labels on the actual links.
- Mini App source evidence now strips redundant prefixes such as
  `Original post:`, removes visible `[link]` placeholders, and adds a short
  "Worth opening..." hint derived from changed fields or priority context, so
  users can decide whether jumping to Telegram is worth the interruption.
- Mini App now has scoped product polish for the mobile review moment:
  product-readable status copy, sound cues with an accessible mute toggle,
  Telegram haptic feedback when the client supports it, signal-colored light
  effects, high-contrast learning-loop and source-discovery copy, Feedback
  expanded-state effects, and reduced-motion safeguards.
- Mini App action receipts now explain the card lifecycle after a tap, including
  where a card moved and when `All`/`Saved` can be used to revisit or undo it.
- Mini App state now exposes packaged public source recommendations, and the
  Mini App can call the same starter-source import path to add or refresh those
  recommended channels for the next run.
- Mini App source recommendations now render as a compact horizontal strip so
  they support the next-run loop without blocking the primary review queue on
  mobile.
- Mini App source discovery now includes next-run outcome copy, clarifies that
  starter adds are metadata-only through compact status chips, makes the
  horizontal channel strip discoverable, and exposes accessible labels for the
  one-tap source action and source cards.
- Mini App now projects a safe `learning_summary` and renders a compact
  learning loop receipt, so mobile users can see whether Review choices are
  ready for a profile draft or whether the next run should validate an applied
  profile change.
- Mini App Learning Loop now uses compact chips for Review choices, draft
  readiness, and evidence freshness, with one short next action instead of
  repeated long draft instructions.
- Source discovery now sits after the primary review list when cards exist; the
  Mini App keeps next-run source helpers available without hiding the first
  Review card behind setup panels.
- Settings > Alerts now distinguishes local Mini App preview from the real
  Telegram entry path, and surfaces the public HTTPS `/miniapp` plus
  `install-miniapp-menu --dry-run` requirement directly in the UI.
- Settings > Alerts now also shows the exact Mini-App-only tunnel command and
  the confirmed real menu button text `Review`.
- Added a static-readiness guard for the Mini App entry so a stale dashboard
  bundle with only `index.html` no longer looks fully ready for Mini App
  acceptance.

## Product Contract Updates

- `ROADMAP.md` now treats public source discovery as candidate-source metadata,
  not message indexing.
- `docs/agent-cli-contract.md` now matches the real Source assistant behavior:
  AI discovery can add only channels copied from sanitized discovered
  candidates, while saved-source operations remain limited to validated source
  ids.
- `README.md` and `README.zh-CN.md` now explain the visible source setup lanes
  and profile-learning loop.
- `docs/public-source-candidates.example.json` captures the future metadata-only
  candidate shape for recommended public sources.
- `docs/agent-cli-contract.md` now separates Review feedback events, profile
  patch drafts, Profile Coach previews, and private JSONL/decision-memory
  export, and it records that current LLM matching is profile-first structured
  extraction rather than vector search.

## External Research Notes

- TGStat and Telemetrio validate public Telegram catalog, ranking, search, and
  analytics demand, but they also reinforce that T-Sense should stay out of the
  public message-indexing business.
- Telega.io validates topic-filtered channel catalog and ad-marketplace
  workflows; T-Sense should borrow the candidate-source review pattern, not the
  advertising transaction model.
- Combot validates group/community analytics and moderation as an adjacent
  category; T-Sense remains a personal source-review and profile-matching loop.
- Telegram Bot Features and Mini Apps docs support the current split: menu
  buttons and Mini Apps are interaction surfaces, not substitutes for local
  MTProto scanning. A 2026-05-17 recheck of the official Mini App and Bot API
  docs did not reveal a required change to the local-first review boundary.
- Direct public-page checks for the packaged starter handles returned HTTP 200
  and visible public messages for `remote_frontend_jobs`, `remote_java_jobs`,
  `remote_ai_jobs`, `remoters`, `unicastjobs`, and `remotejobss`.

References checked on 2026-05-17:

- https://tgstat.org/
- https://telemetr.io/en
- https://telega.io/catalog
- https://combot.org/
- https://core.telegram.org/bots/features
- https://core.telegram.org/bots/webapps

## Verification Evidence

- `.venv/bin/python -m pytest -q`: 697 passed, 2 skipped, 249 subtests passed
- `.venv/bin/python -m ruff check .`: passed
- `npm test -- --run`: 33 files, 247 passed
- `npm run typecheck`: passed
- `npm run build`: passed after the final Mini App/layout and source-starter
  static-entry fixes
- `git diff --check`: passed
- Targeted pytest passed for Mini App static-entry readiness: miniapp-only launch
  auto-builds when `miniapp.html` is missing, and doctor warns for the partial
  static bundle.
- Targeted pytest passed for Mini App menu dry-run preflight: URL/text
  validation works without bot-token loading or Bot API mutation.
- Browser verification:
  - Mini App filter strip stayed `461 x 46`; active filter button stayed
    `110.25 x 34` before and after tapping Priority.
  - Settings > Sources rendered AI folder/all-channel discovery plus pasted
    public links/handles and starter recommendations.
  - Packaged `jobs` starter imports public recommendations instead of returning
    a 0-source install.
  - Packaged starter metadata preserves the public source title, expected
    language, and recommendation notes when imported through Settings.
  - Running the local starter repair removed 5 legacy `example_*` placeholders
    and left 6 active public starter sources with preserved metadata.
  - Public-source Preview accepted `public_source_candidates_v1` JSON and showed
    `remote_jobs` as a no-write source preview.
  - Public-source action buttons fit the Settings source panel at 44px height.
  - Candidate JSON metadata round-trip preserved source label, expected
    language, and recommendation notes into the saved-source row.
  - Saved-source rows keep full public recommendation notes as hover context
    while hiding raw probe fields such as direct page status from visible copy.
  - Profile Coach renders source follow-up suggestions such as "Review noisy
    sources" when backend learning evidence points to source quality.
  - Profile draft cards render a "Why this draft" explanation tied to the Review
    choices that generated the draft.
  - Learning panel renders the Review-to-draft-to-rerun calibration loop with
    current counts.
  - Local miniapp-only preview served `/miniapp` and `/api/miniapp/state` with
    200 responses and blocked `/` plus `/api/settings` with `miniapp_only` 404.
  - Fake-data Mini App QA on `127.0.0.1:8891/miniapp` showed safe
    `Original text` excerpts, labeled `Open in Telegram` links with no visible
    bare Telegram URLs, and the source-discovery recommendation panel.
  - After compacting source discovery, fake-data mobile QA at `390 x 844` showed
    the source-discovery panel at about `243px` high and the first review card
    beginning around `y=566`, keeping card review visible in the first viewport.
  - Fake-data Mini App product QA after adding the learning loop showed useful
    next-action context at a `481 x 832` in-app browser viewport; the first card
    began around `y=519`, source discovery moved after the cards, and no bare
    `https://t.me` text was visible.
  - Browser check for the selected source-evidence block showed
    `Source excerpt`, removed the redundant `Original post:` prefix and `[link]`
    placeholder, rendered `Worth opening to verify Budget and Remote before
    acting.`, kept the labeled `Open in Telegram` action, and still showed no
    bare Telegram URLs.
  - Browser check on `127.0.0.1:8890/miniapp` confirmed the sound toggle
    persists enabled/muted state, unsupported Telegram haptics do not emit new
    warnings, signal light effects are pointer-safe, top status uses
    `Updated ...` product copy instead of raw ISO time, Learning Loop copy is
    readable as a high-contrast panel, Source discovery shows `6 channels ready
    for next run` with `Refresh channels`, Feedback expanded-state has visible
    effects, close button label/visibility works, Duplicate carries negative
    tone/cue, `Jump clue:` is real DOM text, Telegram links expose labels such
    as `Open Miniapps Jobs in Telegram`, and the `481 x 832` mobile viewport has
    no horizontal overflow.
  - Targeted Mini App vitest confirmed lifecycle receipts, accessible card
    action labels, and source-discovery compact status chips plus the channel
    swipe hint, noise tags, and accessible starter-source labels.
  - Targeted Mini App vitest confirmed Learning Loop compact chips for choices,
    draft readiness, and evidence state, plus a short `Review drafts` next
    action.
  - Browser action-receipt QA confirmed `Save` shows `Saved for later / Moved
    to Saved. Open Saved or All to revisit.` and the temporary Mini App QA
    database was restored to the two-card review state afterward.
  - Targeted CSS pytest confirmed Mini App light/effect styling stays scoped to
    cards, state, learning loop, and Feedback panel, and is disabled under
    `prefers-reduced-motion`.
  - Fake-data Mini App QA confirmed the learning loop is useful at the mobile
    review moment: tapping `Feedback` then `Wrong match` immediately showed
    `Feedback saved / 2 learning choices are ready for a profile draft.` and the
    learning panel shifted to profile-draft generation guidance.
  - Settings > Alerts render test confirmed the Mini App preview link appears
    next to the Mini-App-only tunnel command plus the `--text Review`
    `install-miniapp-menu --dry-run` guidance.

## Deferred Decisions

- Whether future public-source recommendation data comes from a curated local
  starter list, a user-imported catalog export, or a live public catalog API.
- Whether LLM matching should remain prompt/structured-output based through
  v0.5, or whether v0.6 needs a vector/embedding layer after user evidence.
- Whether Profile Coach needs a dedicated calibration view before v0.5 is
  called done.
