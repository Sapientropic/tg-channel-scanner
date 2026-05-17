state: miniapp_source_learning_docs_debt_cleanup
mode: Standard
run_shape: remote_sync_plus_publish_prep
slice_goal: "Prepare the Mini App/source-learning/settings work for split commits after syncing origin/master, while keeping the active handoff compact and removing stale verification noise."
authority_note: "This file is only the compact active handoff. Product direction lives in ROADMAP.md; route/agent contracts live in docs/agent-cli-contract.md; platform notes live in docs/desktop-platforms.md; debt guardrails live in docs/technical-debt-cleanup-spec.md; dated quality logs remain historical evidence."
gate_status: passed
blockers: []

current_truth:
  - "Branch: master, synced with origin/master at 2f40a04 before restoring local work."
  - "Restored local Mini App/source-learning/settings changes from stash after remote sync."
  - "Resolved the restore conflicts in docs/quality/task-state.md and tests/test_bot_gateway.py by keeping the new upstream fixes plus the local Mini App additions."
  - "Telegram Mini App remains a local-first review companion: local preview is safe, real Telegram menu install still requires a user-approved public HTTPS /miniapp URL."
  - "Settings should present Mini App install as a normal-user flow: preview locally, paste a public HTTPS link, block local/http links before calling Telegram, then enable the Review menu button."
  - "Public-source intake remains metadata-only: starter recommendations, public links/handles, and candidate JSON must not store raw Telegram message text."
  - "Learning loop remains profile-first structured extraction; profile drafts and coach previews are reviewable user-facing artifacts, not hidden vector matching."

active_scope:
  - "Mini App shell, route boundary, API sanitizers, source recommendations, learning summary, review actions, accessibility, and responsive polish."
  - "Settings source intake, source metadata display/search, learning panel, and Mini App install card."
  - "Bot gateway Mini App menu dry-run/live install, identity repair menu preservation, dashboard miniapp-only static readiness, and doctor checks."
  - "README/ROADMAP/agent contract/platform docs describing the current Mini App, source discovery, and learning behavior."
  - "Document debt cleanup before publishing: keep this handoff compact, keep durable details in authority docs or dated evidence logs, and avoid stale exhaustive verification logs."

verification:
  - "After remote sync, conflict resolution, and document-debt cleanup: dashboard npm test passed with 33 files / 249 tests; dashboard npm run build passed and emitted dist/miniapp.html; .venv/bin/pytest passed with 708 passed, 2 skipped; .venv/bin/ruff check . passed."

next_action: "Split commits by product surface, then push master after a final git status/log check."
