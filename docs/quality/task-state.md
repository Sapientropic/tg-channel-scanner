state: graphify_minimax_automation_configured
mode: Standard
run_shape: focused_doc_refresh_plus_automation_setup
slice_goal: "Keep the technical-debt authority aligned with verified graph/code reality, default Graphify semantic extraction to MiniMax token-plan routing, and keep recurring doc-debt/Graphify sweep records local and ignored."
authority_note: "Compact active handoff only. Current technical-debt status lives in docs/technical-debt-cleanup-spec.md; command recipes live in docs/testing.md; recurring Graphify/doc-debt sweep records live in local ignored docs/graphify-maintenance/; when local graph artifacts exist, generated graph guidance starts at graphify-out/README.md; dated quality logs are historical evidence."
intake_status: explicit_user_request
gate_status: passed
blockers: []
needs_human: []
residual_risk: "graphify-out is gitignored and remains a local generated artifact. Daily sweep records are local-only under gitignored docs/graphify-maintenance/ and excluded from the graph corpus. If the graph is rebuilt after doc cleanup, agents must re-check graphify-out/README.md, GRAPH_REPORT.md, cost.json, needs_update, and the latest local maintenance record before using graph relationships."

current_truth:
  - "Branch at task start: master, clean worktree, one local commit ahead of origin/master."
  - "GitHub issue #7 is closed as of 2026-05-15; its comments remain historical product-debt evidence, not current open debt."
  - "The old quality-iteration implementation details are already summarized in docs/technical-debt-cleanup-spec.md and should not be mirrored here."
  - "Graphify snapshot from 2026-05-15 now contains 3844 nodes, 7194 edges, 32 communities, and 457 inferred edges."
  - "The semantic layer was rebuilt through the MiniMax OpenAI-compatible China route: 57 semantic nodes, 138 semantic edges, 39507 input tokens, and 10904 output tokens."
  - "Graphify skill semantic extraction now defaults to the MiniMax token-plan helper at E:\\CodexHome\\skills\\graphify\\scripts\\extract_minimax_semantic.py, reading MINIMAX_TOKEN_PLAN_KEY before MINIMAX_API_KEY without persisting secrets."
  - "Daily automation tgcs-doc-debt-graphify-sweep is ACTIVE in E:\\CodexHome\\automations and runs this repo's doc-debt/Graphify sweep at 09:30 local time."
  - "docs/graphify-maintenance/ is the local ignored audit trail for recurring sweeps and is excluded from both Git and future graph corpora."
  - "Current code verification shows dashboard_server.py at 1122 lines, review-card.tsx at 907, profile_patches.py at 877, report_extraction.py at 862, desk_scheduler.py at 798, desk_actions.py at 774, sanitize/desk.ts at 697, domain/types.ts at 689, and dashboard_projection.py at 614."
  - "Graph god nodes patch/load_tgcs_module/BotGatewayTests/MonitorStateProjectionTests are primarily test scaffolding signals, not production architecture proof."

active_scope:
  - "docs/technical-debt-cleanup-spec.md: refresh current debt snapshot, large-file signals, Graphify reading conclusions, and next cleanup plan."
  - "docs/quality/task-state.md: keep only compact current handoff."
  - "docs/testing.md: unchanged unless a reusable graph sanity command is needed."
  - "docs/graphify-maintenance/: keep concise same-day audit records for automated doc-debt/Graphify sweeps, but keep the directory gitignored."
  - ".graphifyignore: keep future graph rebuilds away from historical quality logs and generated/private noise."
  - "graphify-out/README.md: local generated guide for agents reading the current graph snapshot when graphify-out is present."

graphify_query_policy:
  - "When graphify-out is present, read graphify-out/README.md before GRAPH_REPORT.md or graph.json."
  - "Treat EXTRACTED anchors as candidates that still need repo-file verification."
  - "Treat INFERRED edges, LLM-only semantic bridges, test helper hubs, and low-cohesion communities as navigation hints."
  - "Check local ignored docs/graphify-maintenance/ records for recent automation outcomes, but do not treat sweep logs as graph evidence."
  - "Never retain graph conclusions directly into long-term memory without checking real files, docs, commands, tests, or issues."

verification:
  - "rg stale-doc sanity check: no stale closed-issue, old-branch, or removed-runtime-settings-file phrases found in the active docs."
  - "git check-ignore -v .graphifyignore returned not ignored; .graphifyignore is now a trackable graph boundary contract."
  - "graphify-out/README.md, GRAPH_REPORT.md, graph.json, manifest.json, and cost.json all existed locally during closeout."
  - "git diff --check passed; Git only warned that .gitignore will be normalized to CRLF when touched."
  - "python -m pytest tests/test_skill_contract.py tests/test_profile_templates.py tests/test_packaging_metadata.py -q passed: 10 passed, 5 subtests passed."
  - "MiniMax route smoke passed against https://api.minimaxi.com/v1 with MiniMax-M2.7-highspeed and JSON-only output."
  - "Graphify LLM semantic extraction passed: 38 document files, 39507 input tokens, 10904 output tokens, 57 semantic nodes, 138 semantic edges."
  - "assemble_graph.py passed: 3844 nodes, 7194 edges, 32 communities, graph.html written."
  - "secret scan for concrete MiniMax key patterns in docs and graphify-out passed; only provider variable names remain in docs."
  - "Project memory retained the MiniMax Graphify rebuild procedure without storing keys."
  - "Graphify report sections and graphify query were used as navigation evidence, then checked against real file line counts and symbol locations."
  - "stale-number grep passed for old zero-token Graphify metrics, removed runtime-settings filenames, and old branch/current issue wording."
  - "git diff --check passed; Git only warned that .gitignore will be normalized to CRLF when touched."
  - "python -m pytest tests/test_skill_contract.py tests/test_profile_templates.py tests/test_packaging_metadata.py -q passed after the doc refresh: 10 passed, 5 subtests passed."
  - "extract_minimax_semantic.py compiled under the Graphify Python 3.11 runtime and --help printed the expected CLI contract."
  - "MiniMax helper smoke passed on a temporary one-file Markdown corpus: 4 semantic nodes, 4 semantic edges, 336 input tokens, 811 output tokens, model MiniMax-M2.7-highspeed, key source MINIMAX_TOKEN_PLAN_KEY; temp directory removed."
  - "Graphify skill docs now reference the MiniMax token-plan helper and key fallback without storing key values."
  - "Automation tgcs-doc-debt-graphify-sweep was created and read back from E:\\CodexHome\\automations\\tgcs-doc-debt-graphify-sweep\\automation.toml."
  - "git diff --check passed after automation setup; Git only warned that .gitignore will be normalized to CRLF when touched."
  - "Modified-file secret scan found no concrete MiniMax key, bearer token, or sk-style credential in repo docs or Graphify skill files."
  - "python -m pytest tests/test_skill_contract.py tests/test_profile_templates.py tests/test_packaging_metadata.py -q passed after automation setup: 10 passed, 5 subtests passed."

next_action: "Use docs/technical-debt-cleanup-spec.md for the next cleanup slice. Prefer review-card evidence/source-preview, profile-learning/runtime-settings, report extraction/source evidence, or dashboard_server compatibility-ledger work depending on the next product risk; the daily sweep should update local ignored docs/graphify-maintenance/ before relying on refreshed graph artifacts."
