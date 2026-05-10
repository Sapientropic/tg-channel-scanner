import { describe, expect, it } from "vitest";

import { buildRunHealthDecision } from "./runs";
import type { Run } from "../domain/types";

function run(overrides: Partial<Run>): Run {
  return {
    run_id: "run-1",
    profile_id: "jobs-fast",
    status: "complete",
    started_at: "2026-05-10T00:00:00Z",
    ...overrides,
  };
}

describe("run health decision", () => {
  it("prioritizes failed runs over card volume", () => {
    expect(buildRunHealthDecision([
      run({ status: "failed", review_card_count: 4, alert_count: 2 }),
      run({ run_id: "run-2", review_card_count: 8, alert_count: 3 }),
    ])).toMatchObject({
      tone: "danger",
      headline: "Fix 1 failed run",
    });
  });

  it("turns diagnostics into a concrete next action", () => {
    expect(buildRunHealthDecision([
      run({
        quality: {
          diagnostic_count: 1,
          diagnostic_warning_count: 1,
          top_diagnostic_code: "llm_unavailable",
        },
      }),
    ])).toMatchObject({
      tone: "warn",
      headline: "Diagnostics need attention",
      detail: "Next: check LLM key",
    });
  });

  it("promotes Review when alert candidates exist", () => {
    expect(buildRunHealthDecision([
      run({ review_card_count: 5, alert_count: 2 }),
    ])).toMatchObject({
      tone: "info",
      headline: "Review 2 alert candidates",
    });
  });
});
