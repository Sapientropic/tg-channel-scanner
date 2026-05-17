# Telegram Mini App Acceptance Checklist

Date: 2026-05-17

## Purpose

Use this checklist for the 5 PM acceptance pass. The default acceptance path is
local Mini-App-only preview with sample review cards. Real Telegram menu
installation is a separate operator-approved step because it needs a public
HTTPS `/miniapp` URL.

## Official Constraints Rechecked

- Telegram menu-button launch is supported through Bot API
  `setChatMenuButton` with `MenuButtonWebApp`.
- `WebAppInfo.url` must be an HTTPS Web App URL.
- Mini App backend requests must validate `Telegram.WebApp.initData` and check
  `auth_date` freshness before trusting user/chat data.
- The current local-first boundary still fits these constraints: the public
  tunnel must point only at `tgcs dashboard --miniapp-only`, and local QA may
  use `--miniapp-allow-loopback-preview`.

Official references rechecked on 2026-05-17:

- https://core.telegram.org/bots/api#setchatmenubutton
- https://core.telegram.org/bots/api#menubuttonwebapp
- https://core.telegram.org/bots/api#webappinfo
- https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

## Local Acceptance Path

1. Build the dashboard bundle:

   ```bash
   cd dashboard
   npm run build
   cd ..
   ```

2. Start a Mini-App-only local preview. For an empty real database:

   ```bash
   ./tgcs dashboard --miniapp-only --port 8890 --miniapp-allow-loopback-preview
   ```

   For a product acceptance demo, use a temporary QA database under
   `/private/tmp` with seeded Review cards. Do not seed `.tgcs/tgcs.db` for a
   demo pass.

3. Open:

   ```text
   http://127.0.0.1:8890/miniapp
   ```

4. Verify the Mini-App-only boundary:

   ```bash
   curl -i --max-time 5 http://127.0.0.1:8890/miniapp
   curl -i --max-time 5 http://127.0.0.1:8890/api/miniapp/state
   curl -i --max-time 5 http://127.0.0.1:8890/
   ```

   Expected:

   - `/miniapp` returns `200`.
   - `/api/miniapp/state` returns `200`.
   - `/` returns `404` with `miniapp_only`.

## Product Acceptance Checks

- The menu-button text for real install is `Review`.
- The first screen shows Review context, not a generic landing page.
- Status copy should be readable product text such as `Updated 05-17 17:32`,
  not a raw ISO timestamp.
- Cards show incremental `Source excerpt` evidence rather than duplicated
  labels such as `Original post:` or fake link placeholders such as `[link]`.
- Card meta should not repeat proof-chip evidence such as `New` or changed
  fields; it should add opportunity status and update time.
- Telegram source jumps render as labeled actions such as `Open in Telegram`,
  not visible bare URLs, and expose accessible labels that include the source
  name.
- Source evidence hints such as `Jump clue:` are real text, not only CSS
  decoration.
- The learning loop uses compact visual tags for choices, draft readiness, and
  evidence freshness, with one short next action; it should not repeat long
  draft instructions.
- Source discovery is available but appears after the primary review cards when
  cards exist; it should show whether channels are ready or still need to be
  added for the next run.
- Source discovery should use compact visual tags instead of stacked
  explanatory copy; it must show ready/to-add, next-run, and metadata-only state,
  plus a visible swipe hint for the channel strip.
- Tapping a lifecycle action such as Applied, Save, Not a fit, Reopen, or Undo
  should explain where the card moved and where the user can revisit or undo it.
- Tapping a Feedback action shows a specific learning receipt, not only a vague
  saved message.
- Sound cues can be muted and re-enabled from the top bar; haptics are used only
  when the Telegram client supports them.
- Light effects are subtle state feedback on cards/status/learning loop, do not
  block taps, and are disabled by reduced-motion settings.
- Review filters should expose their result counts to assistive tech, and
  primary card actions should keep a 44px mobile touch target.
- Feedback has a visible expanded state and the tuning panel should feel like an
  active review/editing mode, not a plain hidden form.
- Feedback close must be a visible, labeled control, and destructive/negative
  tuning actions such as Duplicate should carry matching visual tone.

## Real Telegram Dry-Run

Only after the user provides the public HTTPS URL:

```bash
./tgcs bot install-miniapp-menu --url https://example.com/miniapp --text Review --dry-run
```

Expected:

- The URL is accepted only if it is public HTTPS.
- The command validates text and URL without loading the bot token.
- `menu_button_updated` remains false.

## Live Install

Run only after the dry-run output is accepted and the user explicitly approves
changing the bot menu:

```bash
./tgcs bot install-miniapp-menu --url https://example.com/miniapp --text Review
```

Live install updates only the bot menu button. It does not host the Mini App,
start a webhook, or expose the full Signal Desk dashboard.

## Rollback And Stop

- Stop the local preview by terminating the dashboard process on the chosen
  port.
- If a live menu install must be reverted, set a known-good menu URL again or
  use BotFather/Bot API to restore the default menu button.
- Do not expose the full dashboard port through a public tunnel. Public tunnels
  should terminate at `tgcs dashboard --miniapp-only`.

## Remaining User Decisions

- Public HTTPS `/miniapp` URL for real Telegram menu testing.
- Explicit approval before running the non-dry-run `install-miniapp-menu`
  command.
