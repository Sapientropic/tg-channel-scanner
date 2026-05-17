# Telegram Mini App Landing Notes

Date: 2026-05-17

## Conclusion

Telegram Mini App is landed as a local-first review companion. It reuses the
existing Review card pipeline and writes only existing allowlisted card actions.
It is not a second scanner, a Telegram session holder, or a raw-message archive.

## Product Boundary

- Local preview: `/miniapp`
- Desktop discovery: Settings > Alerts > Open Mini App preview
- Acceptance checklist:
  `docs/quality/2026-05-17-miniapp-acceptance-checklist.md`
- Public tunnel boundary: `./tgcs dashboard --miniapp-only --port 8778`
- Telegram install preflight:
  `./tgcs bot install-miniapp-menu --url https://example.com/miniapp --text Review --dry-run`
- Telegram live install command:
  `./tgcs bot install-miniapp-menu --url https://example.com/miniapp --text Review`
- Telegram-hosted use requires a public HTTPS URL, but the installer only
  registers the menu URL. It does not provide hosting, webhook delivery, or
  public ingress.

## Architecture

- `scripts/desk_miniapp.py` owns Telegram Mini App auth, safe state projection,
  and loopback preview authorization.
- `scripts/desk_miniapp_routes.py` owns the narrow `/api/miniapp/*` HTTP
  contract and delegates card mutation to `monitor_state`.
- `scripts/dashboard_server.py` serves `/miniapp` and routes Mini App API calls
  before ordinary dashboard routes. In `--miniapp-only` mode it blocks ordinary
  dashboard APIs, artifacts, the desktop index, and desktop-only static bundles.
- `dashboard/src/miniapp.tsx` is an independent mobile review entrypoint, not a
  sixth tab in the desktop dashboard.
- `dashboard/src/domain/sanitize/miniapp.ts` keeps the frontend contract small
  and strips auth fields or report artifact paths that should not be rendered
  for signed Telegram users.

## Current User-Facing Capabilities

- Queue summary: Priority, Review, Saved, Total
- Filters: Review, Priority, Saved, Handled/Duplicate when present, All
- Card actions: Applied, Save, Not a fit, Reopen
- Feedback actions: Prefer similar, Deprioritize, Wrong match, Duplicate, note
- Safe links: Telegram message/channel refs, plus local report artifacts only
  in loopback preview mode
- Source evidence: the Mini App strips redundant source prefixes such as
  `Original post:` plus visible `[link]` placeholders, and adds a semantic
  `Jump clue:` hint explaining when opening the Telegram original is useful.
- Interaction polish: review actions have scoped sound cues, an accessible
  sound toggle, Telegram haptic feedback when the client supports it, and
  signal-colored light effects that respect reduced-motion settings. The status
  line uses product-readable `Updated ...` copy instead of raw ISO timestamps.
  Learning Loop and Source discovery copy are rendered as high-contrast panels,
  and Feedback has a distinct expanded state.
- Mobile evidence chips mirror desktop Review context for new/updated/repeated
  cards, changed fields, and Telegram alert proof.
- Multiple safe Telegram source links are shown on each card, with duplicate
  URLs collapsed and overflow counted.
- Full dashboard local preview works without Telegram `initData`. The
  `--miniapp-only` public boundary requires signed Telegram Mini App init data
  by default; `--miniapp-allow-loopback-preview` is reserved for local QA.
- Action responses return the same Mini App card projection as state reads, not
  the full local Review card row.
- Successful Review/Profile-tuning actions now surface a compact status message
  in the Mini App header so users can see where the card moved and how to
  revisit or undo it.
- The Mini App now renders a safe learning-loop panel from `learning_summary`,
  showing saved Review choices, pending profile drafts, evidence freshness, and
  the next Desk action as compact status chips without exposing local export
  paths or private feedback rows.
- Source discovery remains available for next-run setup, but it renders after
  the review list when cards exist so the first card stays visible on mobile.
- Source discovery now tells users what the next run gains from starter
  channels through compact status chips, distinguishes metadata-only source adds
  from future card evidence, makes the horizontal channel strip discoverable,
  and exposes accessible labels on the source action and source cards.
- Forwarded remote dashboard or Mini App requests are not accepted as
  loopback-only access.
- Static readiness now includes the Mini App entry itself: `doctor` warns when
  the dashboard bundle has `index.html` but lacks `miniapp.html`, and
  `tgcs dashboard --miniapp-only` auto-builds the default bundle when that entry
  is missing.
- The Mini App menu installer has a dry-run preflight so the public HTTPS URL
  and button text can be validated before any live Bot API menu update.

## Verification Evidence

- `npm test -- --run`: 33 files, 247 passed
- `npm run typecheck`: passed
- `npm run build`: passed
- `.venv/bin/python -m pytest -q`: 697 passed, 2 skipped, 249 subtests passed
- `.venv/bin/python -m ruff check .`: passed
- `git diff --check`: passed
- Targeted static-readiness tests:
  `tests/tgcs_cli/test_delegates.py::TgcsDelegateTests::test_dashboard_miniapp_only_auto_builds_when_miniapp_entry_is_missing`
  plus the related `doctor` pass/warn tests passed.
- Targeted Bot Gateway tests passed: Mini App menu dry-run validates URL/text,
  skips API mutation, and does not require a bot token.
- Browser checks:
  - `/miniapp` empty state: no horizontal overflow
  - `/miniapp` with sample review cards at 390px mobile width: no horizontal
    overflow; filters, source links, status chips, and review actions render
    coherently
  - Local browser preview has no Mini App app-console warnings after guarding
    newer Telegram theme APIs by WebApp version
  - Settings > Alerts: "Open Mini App preview" renders with `/miniapp`
  - Mini-App-only boundary blocks ordinary `/api/state`, `/artifacts/*`, and
    desktop dashboard asset bundles
  - Mini-App-only boundary rejects no-initData API reads by default; local QA
    preview uses explicit `--miniapp-allow-loopback-preview`
  - Mini App filter strip stayed `461 x 46`; active filter button stayed
    `110.25 x 34` before and after tapping Priority.
  - Mini App profile-tuning action showed `Feedback saved` /
    `2 learning choices are ready for a profile draft.` after tapping
    `Wrong match` in the product-QA fake data.
  - Mini App product QA showed the learning loop while keeping the first Review
    card visible at about `y=519` in a `481 x 832` in-app browser viewport; the
    source-discovery panel appeared after the card list.
  - Targeted Mini App tests confirmed the Learning Loop uses compact status
    chips for choices, draft readiness, and evidence state, shortens the next
    action to `Review drafts`, and removes repeated long draft instructions from
    the mobile shell.
  - Mini App source evidence rendered as `Source excerpt`, removed the duplicate
    `Original post:` prefix and `[link]` placeholder, and showed `Worth opening
    to verify Budget and Remote before acting.` while preserving labeled `Open
    in Telegram` links.
  - Mini App polish verification on `127.0.0.1:8890/miniapp`: the sound toggle
    persisted enabled/muted state, unsupported Telegram haptics produced no new
    warnings after version gating, scoped light effects did not block pointer
    interactions, top status showed `Updated 05-17 17:32` instead of raw ISO
    time, Learning Loop copy became readable in a high-contrast panel, Source
    discovery showed `6 channels ready for next run` with `Refresh channels`,
    Feedback expanded-state showed visible effects, close button label/visibility
    worked, Duplicate carried negative tone/cue, `Jump clue:` rendered as real
    DOM text, Telegram links exposed accessible labels like
    `Open Miniapps Jobs in Telegram`, and the `481 x 832` mobile viewport had no
    horizontal overflow.
  - Targeted Mini App tests confirmed lifecycle receipts such as `Moved out of
    Review. Open All if you need to undo.`, compact source-discovery status
    chips, the channel swipe hint, noise tags, and accessible labels for card
    actions, starter-source actions, and source cards.
  - Browser action-receipt QA on `127.0.0.1:8890/miniapp`: tapping `Save`
    showed `Saved for later / Moved to Saved. Open Saved or All to revisit.`;
    the temporary QA database was restored to two pending review cards after the
    check.
  - Local miniapp-only preview on `127.0.0.1:8890` served `/miniapp` and
    `/api/miniapp/state` with 200 responses, while `/` and `/api/settings`
    returned `miniapp_only` 404.

## Current Preview Endpoints

- Full local dashboard: `http://127.0.0.1:8777/`
- Full local Mini App preview: `http://127.0.0.1:8777/miniapp`
- Safe Mini-App-only tunnel target: `http://127.0.0.1:8779/miniapp`
- Local QA Mini-App-only preview with sample cards:
  `http://127.0.0.1:8780/miniapp`
- Do not expose `8777` through a public tunnel. For a real Telegram test, expose
  the Mini-App-only boundary and install that public HTTPS `/miniapp` URL.

## External Contract References

- Telegram Mini Apps / Web Apps: https://core.telegram.org/bots/webapps
- Telegram Bot API menu button: https://core.telegram.org/bots/api

Verified on 2026-05-17 against the official Telegram docs: Mini App init data
uses the Telegram WebApp validation flow with `auth_date` freshness checks,
`WebAppInfo.url` is an HTTPS URL, and menu-button installation is a Bot API
`setChatMenuButton` operation with `MenuButtonWebApp`. The local installer keeps
the stricter project rule that the URL must be public HTTPS. Telegram's April
2026 Mini App additions do not require changing the current local-first review
boundary.

## Deferred Decisions

- Public HTTPS host for the real Telegram menu button.
- Menu button text is confirmed as `Review`; live install still needs the public
  HTTPS `/miniapp` URL and explicit approval for the non-dry-run command.
- Whether to add a hosted ingress boundary later. Current implementation is
  deliberately local-first plus signed Telegram init data.
- Public menu URL must be real public HTTPS. Localhost, loopback, and private IP
  addresses are rejected by the installer. Use
  `tgcs bot install-miniapp-menu --url <https>/miniapp --text Review --dry-run`
  for a no-side-effect preflight before any live Bot API menu update.
- Whether Mini App should later expose profile-coach draft actions. Current
  scope only records review feedback for later tuning.
