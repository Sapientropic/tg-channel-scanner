import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { LearningPanel, feedbackExportStatusLine, learningActionLabel } from "./learning-panel";

describe("Learning panel copy", () => {
  it("turns a feedback export result into an app-native status line", () => {
    expect(
      feedbackExportStatusLine({
        schema_version: "feedback_export_result_v1",
        feedback_count: 3,
        output_path: "output/feedback/review-feedback.jsonl",
        changed_since_last_export: false,
        exported_at: "2026-05-10T00:00:00Z",
      }),
    ).toBe("3 decisions applied to future reports · output/feedback/review-feedback.jsonl");
  });

  it("uses app-first wording for the primary learning action", () => {
    expect(learningActionLabel(0)).toBe("Collect review decisions");
    expect(learningActionLabel(2)).toBe("Apply feedback to future reports");
  });

  it("keeps clear action clickable even when there are no current decisions", () => {
    const html = renderToStaticMarkup(
      createElement(LearningPanel, {
        busy: false,
        clearFeedback: () => undefined,
        exportFeedback: () => undefined,
        exportResult: null,
        runAgainWithLearning: () => undefined,
        summary: { current_decision_count: 0, exportable_count: 0 },
        undoFeedbackDecision: () => undefined,
      }),
    );

    expect(html).toContain("Clear learning decisions");
    expect(html).not.toMatch(/<button class="text-button secondary"[^>]*disabled[^>]*>[\s\S]*?Clear learning decisions/);
  });
});
