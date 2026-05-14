import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { ValidationSummaryPanel } from "./board-status";

describe("ValidationSummaryPanel", () => {
  it("surfaces time to first useful decision in the proof loop", () => {
    const html = renderToStaticMarkup(
      <ValidationSummaryPanel
        summary={{
          schema_version: "dashboard_validation_summary_v1",
          window_days: 14,
          runs_count: 1,
          card_count: 3,
          high_card_count: 2,
          pending_count: 0,
          action_count: 3,
          by_action: { keep: 1, false_positive: 1, follow_up: 1 },
          first_decision_minutes: 7,
          first_decision_action: "keep",
          next_action: { label: "Keep validation cadence", detail: "Record concrete outcomes." },
        }}
      />,
    );

    expect(html).toContain("First decision");
    expect(html).toContain("7 min (keep)");
  });
});
