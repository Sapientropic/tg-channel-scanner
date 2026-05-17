import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { LearningPanel, feedbackExportStatusLine, feedbackSuggestionStatusLine, learningActionLabel } from "./learning-panel";

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
    ).toBe("3 decisions saved for learning");
  });

  it("summarizes generated profile drafts without making JSONL the happy path", () => {
    expect(
      feedbackSuggestionStatusLine({
        schema_version: "feedback_profile_suggestions_result_v1",
        created_count: 1,
        existing_count: 2,
        skipped_count: 0,
        patch_ids: ["patch-1", "patch-2"],
        profile_ids: ["jobs-fast"],
      }),
    ).toBe("1 draft created · 2 already waiting");
  });

  it("uses app-first wording for the primary learning action", () => {
    expect(learningActionLabel(0)).toBe("Review cards");
    expect(learningActionLabel(2)).toBe("Suggest improvements");
    expect(learningActionLabel(2, 1)).toBe("Review profile drafts");
  });

  it("sends the empty learning state back to Review instead of showing a dead draft action", () => {
    const html = renderToStaticMarkup(
      createElement(LearningPanel, {
        busy: false,
        clearFeedback: () => undefined,
        exportFeedback: () => undefined,
        exportResult: null,
        generateProfileSuggestions: () => undefined,
        openProfileDrafts: () => undefined,
        openReviewCards: () => undefined,
        runAgainWithLearning: () => undefined,
        summary: { current_decision_count: 0, exportable_count: 0 },
        suggestionResult: null,
        undoFeedbackDecision: () => undefined,
      }),
    );

    expect(html).toContain("Review cards");
    expect(html).toContain("Clear learning decisions");
    expect(html).toMatch(/<button class="text-button secondary"[^>]*disabled[^>]*>[\s\S]*?Clear learning decisions/);
    expect(html).not.toContain("Collect review decisions");
    expect(html).not.toContain("output/feedback/review-feedback.jsonl");
  });

  it("renders calibration evidence for profile tuning decisions", () => {
    const html = renderToStaticMarkup(
      createElement(LearningPanel, {
        busy: false,
        clearFeedback: () => undefined,
        exportFeedback: () => undefined,
        exportResult: null,
        generateProfileSuggestions: () => undefined,
        openProfileDrafts: () => undefined,
        openReviewCards: () => undefined,
        runAgainWithLearning: () => undefined,
        summary: {
          current_decision_count: 5,
          exportable_count: 3,
          pending_profile_diff_count: 1,
          applied_profile_diff_count: 2,
          reverted_profile_diff_count: 1,
          by_action: { keep: 1, skip: 1, false_positive: 1 },
          by_rating: { high: 2 },
          by_decision_status: { changed: 1 },
          calibration: {
            schema_version: "feedback_calibration_summary_v1",
            latest_applied_at: "2026-05-13T01:00:00Z",
            runs_after_latest_apply: 1,
            cards_after_latest_apply: 3,
            high_cards_after_latest_apply: 2,
            feedback_after_latest_apply: 1,
            false_positive_after_latest_apply: 1,
            high_rate_after_latest_apply: 2 / 3,
            next_action: { label: "Tune remaining false positives", detail: "Wrong matches still appeared." },
          },
        },
        suggestionResult: null,
        undoFeedbackDecision: () => undefined,
      }),
    );

    expect(html).toContain('aria-label="Feedback calibration evidence"');
    expect(html).toContain('aria-label="Learning loop progress"');
    expect(html).toContain("Learning loop");
    expect(html).toContain("Review choices");
    expect(html).toContain("Create draft");
    expect(html).toContain("Apply draft");
    expect(html).toContain("Run again");
    expect(html).toContain("Calibrate");
    expect(html).toContain("5 ready");
    expect(html).toContain("1 waiting");
    expect(html).toContain("2 applied");
    expect(html).toContain("1 run");
    expect(html).toContain("Preferred 1");
    expect(html).toContain("Wrong match 1");
    expect(html).toContain("High priority 2");
    expect(html).toContain("Applied changes 2");
    expect(html).toContain("Reverted changes 1");
    expect(html).toContain("reverted");
    expect(html).toContain('aria-label="Next-run calibration evidence"');
    expect(html).toContain("After latest update");
    expect(html).toContain("Tune remaining false positives");
    expect(html).toContain("Review profile drafts");
    expect(html).toContain("Runs 1");
    expect(html).toContain("Cards 3");
    expect(html).toContain("High rate 67%");
  });

  it("renders the profile coach loop with reviewed suggestions and selected-profile run action", () => {
    const html = renderToStaticMarkup(
      createElement(LearningPanel, {
        busy: false,
        clearFeedback: () => undefined,
        exportFeedback: () => undefined,
        exportResult: null,
        generateProfileSuggestions: () => undefined,
        openProfileDrafts: () => undefined,
        openReviewCards: () => undefined,
        runAgainWithLearning: () => undefined,
        summary: {
          current_decision_count: 3,
          exportable_count: 1,
          non_exportable_follow_up_count: 2,
          pending_profile_diff_count: 0,
          applied_profile_diff_count: 1,
        },
        suggestionResult: null,
        undoFeedbackDecision: () => undefined,
        profiles: [
          {
            profile_id: "jobs-fast",
            display_name: "Jobs Fast",
            enabled: true,
            updated_at: "2026-05-10T00:00:00Z",
          },
        ],
        profileCoachPreview: {
          schema_version: "profile_coach_preview_v1",
          status: "ready",
          profile_id: "jobs-fast",
          evidence_counts: { keep: 1, skip: 0, false_positive: 1, follow_up: 2 },
          diagnosis: [{ label: "Wrong matches", detail: "Recurring full-stack roles need a clearer exclusion." }],
          suspected_false_positive_patterns: ["full-stack generalist roles"],
          suggested_preference_rules: ["Exclude full-stack roles unless frontend ownership is explicit."],
          source_suggestions: [
            {
              kind: "review_sources",
              label: "Review noisy sources",
              detail: "If wrong matches come from the same channel, review that source before changing the profile.",
            },
          ],
          confidence: "medium",
          warnings: [],
          llm_used: true,
        },
        previewProfileCoach: () => undefined,
        createProfileMatchingPreferencesDraft: () => undefined,
      }),
    );

    expect(html).toContain("Profile Coach");
    expect(html).toContain("Tune this profile from Review choices");
    expect(html).toContain("Suggestions run only when you ask");
    expect(html).toContain("Suggest improvements");
    expect(html).not.toContain("Coach diagnosis");
    expect(html).not.toContain("Profile/source");
    expect(html).not.toContain("Run and validate");
    expect(html).not.toContain("LLM");
    expect(html).toContain("Wrong matches");
    expect(html).toContain("Exclude full-stack roles");
    expect(html).toContain("Review noisy sources");
    expect(html).toContain("review that source before changing the profile");
    expect(html).toContain("Create draft to review");
    expect(html).toContain("Run this profile again");
  });
});
