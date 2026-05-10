import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { InboxView } from "./inbox";
import type { ReviewCard } from "../domain/types";

function card(overrides: Partial<ReviewCard> = {}): ReviewCard {
  return {
    schema_version: "review_card_v1",
    card_id: "card-1",
    profile_id: "jobs-fast",
    title: "Frontend Developer",
    rating: "high",
    decision_status: "new",
    source_refs: [{ channel: "javascript_jobs", id: 42 }],
    item: { why: "Remote React role with a clear salary range." },
    status: "pending",
    first_run_id: "run-1",
    last_run_id: "run-1",
    report_path: "reports/jobs.html",
    updated_at: "2026-05-11T01:42:00+08:00",
    ...overrides,
  };
}

describe("InboxView", () => {
  it("keeps the compact mobile filter control accessible", () => {
    const html = renderToStaticMarkup(
      <InboxView
        cards={[card()]}
        latestRunId="run-1"
        profileReportNames={{ "jobs-fast": "Jobs Report" }}
        act={vi.fn()}
        busy={false}
      />,
    );

    expect(html).toContain('aria-label="Review filter: Latest action (1)"');
    expect(html).toContain("Latest");
    expect(html).toContain("Frontend Developer");
    expect(html).toContain("Keep");
    expect(html).toContain("Tune profile");
  });
});
