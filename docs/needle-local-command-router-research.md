# Needle Local Command Router Research

**Status**: research note captured on 2026-05-15. Do not treat this as a
committed product plan.

This note records whether Cactus Needle is a good candidate for the local
natural-language command mapping layer in the T-Sense Telegram Bot Gateway.
The product boundary remains in `agent-cli-contract.md`: Telegram text may only
map to fixed local actions and must never become shell, argv, file paths,
tokens, or arbitrary model output.

## Short Answer

Needle is worth testing as a local intent router, but not as the default
production path yet.

The recommended future shape is:

1. keep deterministic routing first;
2. try Needle only for unresolved safe free text;
3. validate Needle output through the existing `bot_intent_v1` schema and
   allowlist;
4. fall back to the current OpenAI-compatible LLM route or local
   `deterministic-no-llm` behavior when confidence, JSON, or validation fails.

Needle should be an action translation layer, not a general assistant.

## What Needle Appears To Be

Needle is a very small function-calling model from Cactus Compute. The public
materials describe it as:

- a 26M parameter model focused on single-shot tool/function calling;
- MIT-licensed model code/weights in the Needle repository and Hugging Face
  model card;
- a JAX/Flax implementation with weights published as a pickle artifact;
- designed for local or edge inference rather than chat-quality general
  reasoning;
- trained to map user input plus a tool list into a structured tool call.

[⚠️ 需确认] The public performance and training details are primarily from the
vendor's own README/model card and launch discussion. They are promising, but
they are not a substitute for testing against our own bot command corpus.

## Fit With T-Sense

The fit is strong for the narrow layer we care about:

- The Telegram Bot Gateway already has a small intent surface:
  `status`, `latest`, `profiles`, `settings`, `sources_summary`,
  `sources_plan`, and `scan_profile_dry_run`.
- `scripts/bot_intents.py` already treats model output as untrusted JSON and
  accepts it only through `validate_llm_intent_payload()`.
- `docs/agent-cli-contract.md` already says bot messages map only to fixed
  local actions and never accept shell, file paths, argv, tokens, raw Telegram
  message text, or live delivery commands.
- Source mutations already use preview/apply semantics, so a local intent
  router can propose `sources_plan` without being allowed to write directly.

This means Needle can be slotted in as another intent provider without changing
the safety model.

## Where It Should Not Be Used

Do not use Needle for these paths unless a later benchmark proves otherwise:

- open-ended knowledge answers;
- semantic source discovery over many Telegram channels;
- selecting channels against long profile text;
- live delivery or destructive operations;
- any route that would require accepting arbitrary paths, command strings, or
  model-generated argv.

Needle's useful boundary is "which fixed safe action did the user mean?", not
"reason over the whole product state."

## Proposed Integration Sketch

Add a local provider behind the existing router, roughly:

```text
deterministic_intent(text)
  -> if matched, return it
needle_intent(text, tools=bot_intent_v1 tool list)
  -> validate_llm_intent_payload(payload)
  -> if valid and confidence is acceptable, return it
llm_intent(text)
  -> validate_llm_intent_payload(payload)
fallback deterministic-no-llm knowledge_answer
```

Keep Needle opt-in at first:

- environment flag such as `TGCS_BOT_LOCAL_INTENT_PROVIDER=needle`;
- optional extra dependency, not part of the base install;
- pinned model revision and checksum;
- no raw Telegram private text in training or vendor playground data.

Use the same product-shaped JSON as the current LLM route:

```json
{
  "schema_version": "bot_intent_v1",
  "action": "status",
  "confidence": "high",
  "source": "llm",
  "args": {},
  "needs_confirmation": false,
  "safe_reply": ""
}
```

If we later add a dedicated source value such as `"needle"`, update validation,
fixtures, and dashboard diagnostics together so downstream consumers do not
silently assume cloud LLM behavior.

## Acceptance Gate Before Default Enablement

Before making Needle the default local intent layer, build a small fixture set:

- 100-200 realistic English/Chinese Telegram bot messages;
- direct command variants: status/latest/profiles/settings/sources/scan;
- fuzzy requests: "看看现在配好了没", "跑一次 jobs-fast", "给我最新卡片";
- unsafe probes: shell, PowerShell, paths, argv, tokens, live delivery requests;
- ambiguous text that should fall back to knowledge answer.

Minimum bar:

- zero unsafe action escapes;
- no shell/path/argv/token fields accepted in any payload;
- at least 95% accuracy on common safe action routing;
- invalid JSON or unknown actions always fall back safely;
- `sources_plan` still requires preview/apply confirmation;
- Windows smoke confirms the dependency stack installs cleanly.

If these gates are not met, keep Needle as an experiment only.

## Implementation Risks

- JAX/Flax is a larger optional dependency than the current bot gateway needs.
  On Windows it must be smoke-tested before documenting it as supported.
- The public Cactus runtime license has different commercial terms from the
  Needle model repository. Prefer direct Needle/JAX POC first; do not assume the
  full Cactus runtime is product-compatible.
- Hugging Face pickle weights should be treated as executable-load risk:
  pin revisions, verify checksums, and load only from a trusted install path.
- The launch discussion includes reports of ambiguous tool selection. Our
  action set is smaller than general function-calling benchmarks, but we still
  need local fixtures.
- Fine-tuning data must be synthetic or sanitized. Do not upload private
  Telegram text, chat ids, tokens, source registry internals, or local paths.

## Recommendation

Park this as a future v0.6 experiment.

The next useful slice is not "wire it into production"; it is:

1. add a fixture-only `needle_intent` prototype behind a feature flag;
2. run it against the bot intent corpus;
3. compare it with deterministic routing and current cloud LLM fallback;
4. decide whether it reduces latency/cost without weakening the safety boundary.

Until then, keep the current deterministic-first router and existing optional
LLM fallback.

## Sources Checked

- Cactus Needle GitHub repository:
  <https://github.com/cactus-compute/needle>
- Needle Hugging Face model card:
  <https://huggingface.co/Cactus-Compute/needle>
- Cactus Python documentation:
  <https://docs.cactuscompute.com/latest/python/>
- Cactus runtime license:
  <https://raw.githubusercontent.com/cactus-compute/cactus/main/LICENSE>
- JAX installation documentation:
  <https://docs.jax.dev/en/latest/installation.html>
- Hacker News launch discussion:
  <https://news.ycombinator.com/item?id=48111896>

