import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { CommandStrip, OpportunitySummaryPanel, ValidationSummaryPanel } from "./board-status";
import { emptyDashboardState } from "../domain/sanitize";

describe("ValidationSummaryPanel", () => {
  it("surfaces time to first useful decision in the review window", () => {
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

    expect(html).toContain("First action");
    expect(html).toContain("7 min (keep)");
    expect(html).toContain("Keep rate");
    expect(html).toContain("33%");
    expect(html).toContain("Wrong match 1");
    expect(html).not.toContain("false_positive");
  });

  it("normalizes older proof-heavy validation copy", () => {
    const html = renderToStaticMarkup(
      <ValidationSummaryPanel
        summary={{
          schema_version: "dashboard_validation_summary_v1",
          window_days: 14,
          runs_count: 1,
          card_count: 3,
          high_card_count: 2,
          pending_count: 3,
          action_count: 0,
          by_action: {},
          next_action: {
            label: "Review cards",
            detail: "Mark keep, skip, false positive, or follow-up so the validation window has behavior evidence.",
          },
        }}
      />,
    );

    expect(html).toContain("Mark what happened so future matches improve.");
    expect(html).not.toContain("behavior evidence");
  });

  it("normalizes older action-signal opportunity labels", () => {
    const html = renderToStaticMarkup(
      <OpportunitySummaryPanel
        summary={{
          profile_id: "jobs-fast",
          status: "ready",
          display_name: "Developer Opportunity",
          scanned_count: 10,
          matched_count: 3,
          review_card_count: 1,
          high_actionable_count: 1,
          next_action: { label: "Review action signals", detail: "Review cards." },
        }}
      />,
    );

    expect(html).toContain("Review priority cards");
    expect(html).not.toContain("Review action signals");
  });

  it("uses current inbox state to clear stale priority summary counts", () => {
    const html = renderToStaticMarkup(
      <OpportunitySummaryPanel
        latestPriorityCount={0}
        summary={{
          profile_id: "jobs-fast",
          status: "ready",
          display_name: "Developer Opportunity",
          scanned_count: 10,
          matched_count: 3,
          review_card_count: 1,
          high_actionable_count: 1,
          next_action: { label: "Review priority cards", detail: "Review cards." },
        }}
      />,
    );

    expect(html).toContain("No priority cards");
    expect(html).toContain("Priority");
    expect(html).toContain(">0</strong>");
    expect(html).not.toContain("Review priority cards");
  });

  it("uses current inbox state for handled validation counts", () => {
    const html = renderToStaticMarkup(
      <ValidationSummaryPanel
        cards={[
          {
            schema_version: "review_card_v1",
            card_id: "handled-1",
            profile_id: "jobs-fast",
            title: "Handled role",
            rating: "high",
            decision_status: "new",
            source_refs: [],
            item: {},
            status: "pending",
            opportunity_status: "dismissed",
            opportunity_updated_at: "2026-05-14T00:00:00Z",
            updated_at: "2026-05-14T00:00:00Z",
          },
        ]}
        summary={{
          schema_version: "dashboard_validation_summary_v1",
          window_days: 14,
          runs_count: 16,
          card_count: 52,
          high_card_count: 13,
          pending_count: 52,
          action_count: 0,
          by_action: {},
        }}
      />,
    );

    expect(html).toContain("All review cards handled");
    expect(html).toContain("1 handled card saved as history.");
    expect(html).toContain("Handled");
    expect(html).toContain("1/1");
    expect(html).not.toContain("Waiting");
    expect(html).not.toContain("Reviewed");
    expect(html).not.toContain("Keep rate");
  });

  it("does not count handled cards as needing review", () => {
    const html = renderToStaticMarkup(
      <CommandStrip
        state={{
          ...emptyDashboardState,
          inbox: [
            {
              schema_version: "review_card_v1",
              card_id: "handled-1",
              profile_id: "jobs-fast",
              title: "Handled role",
              rating: "high",
              decision_status: "new",
              source_refs: [],
              item: {},
              status: "pending",
              opportunity_status: "dismissed",
              opportunity_updated_at: "2026-05-14T00:00:00Z",
              updated_at: "2026-05-14T00:00:00Z",
            },
          ],
        }}
        metrics={[]}
      />,
    );

    expect(html).toContain("Review queue");
    expect(html).toContain(">0</strong>");
    expect(html).toContain("1 handled");
    expect(html).not.toContain("cards to decide");
  });
});
