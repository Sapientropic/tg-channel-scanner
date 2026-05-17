import { describe, expect, it } from "vitest";

import { sanitizeMiniAppReviewState } from "./sanitize";

describe("Mini App state sanitizer", () => {
  it("keeps sanitized review cards and safe auth metadata", () => {
    const state = sanitizeMiniAppReviewState({
      schema_version: "miniapp_review_state_v1",
      auth: { schema_version: "telegram_miniapp_auth_v1", source: "telegram", user_id: "123456", chat_id: "secret" },
      generated_at: "2026-05-17T00:00:00Z",
      cards: [
        {
          schema_version: "review_card_v1",
          card_id: "card-1",
          profile_id: "jobs-fast",
          title: "Frontend Mini App contract",
          rating: "high",
          decision_status: "new",
          source_refs: [
            { channel: "miniapps_jobs", id: 42, url: "https://t.me/miniapps_jobs/42" },
            { channel: "bad", id: 1, url: "javascript:alert(1)" },
          ],
          item: {
            why: "Paid React work.",
            source_excerpt: "Original post: React Mini App contract. [link]",
            raw_text: "private raw Telegram message",
            decision_state: { status: "new", explanations: { token: "secret", public: "ok" } },
          },
          status: "pending",
          opportunity_status: "open",
          opportunity_updated_at: "2026-05-17T00:00:00Z",
          report_path: "output/jobs-fast/report.html",
          updated_at: "2026-05-17T00:00:00Z",
          first_run_id: "run-1",
          last_run_id: "run-2",
          alert_summary: {
            alert_count: 1,
            latest_target_id: "telegram-bot-default",
            latest_run_id: "run-secret",
            latest_delivery_status: "sent",
          },
        },
      ],
      source_recommendations: [
        {
          schema_version: "miniapp_source_recommendation_v1",
          source_id: "telegram:remote_frontend_jobs",
          channel: "remote_frontend_jobs",
          label: "Remote Front-End Jobs",
          topic: "jobs",
          reason: "Remote front-end jobs.",
          installed: false,
          raw_text: "private sample post",
          token: "secret",
        },
      ],
      learning_summary: {
        schema_version: "miniapp_learning_summary_v1",
        current_decision_count: 2,
        exportable_count: 1,
        non_exportable_follow_up_count: 1,
        pending_profile_diff_count: 0,
        applied_profile_diff_count: 1,
        changed_since_last_export: true,
        next_action: {
          label: "Suggest profile improvements",
          detail: "Review feedback can generate profile drafts.",
          command: "tgcs secret command",
        },
        calibration_next_action: {
          label: "Run after tuning",
          detail: "A profile diff was applied; run the profile again.",
          command: "tgcs secret command",
        },
        recent_impacts: [{ item_title: "private card" }],
        last_export_path: "private/path.jsonl",
      },
      profiles: [{ profile_id: "jobs-fast", display_name: "Jobs Fast" }],
      token: "secret",
    });

    expect(state).toMatchObject({
      schema_version: "miniapp_review_state_v1",
      auth: { schema_version: "telegram_miniapp_auth_v1", source: "telegram", user_id: "123456" },
      generated_at: "2026-05-17T00:00:00Z",
    });
    expect(state.cards).toHaveLength(1);
    expect(state.cards[0].item.source_excerpt).toBe("Original post: React Mini App contract. [link]");
    expect(state.cards[0].source_refs).toEqual([
      { channel: "miniapps_jobs", id: 42, url: "https://t.me/miniapps_jobs/42" },
      { channel: "bad", id: 1 },
    ]);
    expect(state.source_recommendations).toEqual([
      {
        schema_version: "miniapp_source_recommendation_v1",
        source_id: "telegram:remote_frontend_jobs",
        channel: "remote_frontend_jobs",
        label: "Remote Front-End Jobs",
        topic: "jobs",
        reason: "Remote front-end jobs.",
        installed: false,
      },
    ]);
    expect(state.learning_summary).toEqual({
      schema_version: "miniapp_learning_summary_v1",
      current_decision_count: 2,
      exportable_count: 1,
      non_exportable_follow_up_count: 1,
      pending_profile_diff_count: 0,
      applied_profile_diff_count: 1,
      changed_since_last_export: true,
      next_action: {
        label: "Suggest profile improvements",
        detail: "Review feedback can generate profile drafts.",
      },
      calibration_next_action: {
        label: "Run after tuning",
        detail: "A profile diff was applied; run the profile again.",
      },
    });
    expect(JSON.stringify(state)).not.toContain("private raw Telegram message");
    expect(JSON.stringify(state)).not.toContain("private sample post");
    expect(JSON.stringify(state)).not.toContain("private/path.jsonl");
    expect(JSON.stringify(state)).not.toContain("private card");
    expect(JSON.stringify(state)).not.toContain("secret");
    expect(JSON.stringify(state)).not.toContain("profiles");
    expect(JSON.stringify(state)).not.toContain("run-1");
    expect(JSON.stringify(state)).not.toContain("telegram-bot-default");
    expect(JSON.stringify(state)).not.toContain("output/jobs-fast/report.html");
  });

  it("keeps local report artifact paths only for loopback preview state", () => {
    const state = sanitizeMiniAppReviewState({
      schema_version: "miniapp_review_state_v1",
      auth: { schema_version: "telegram_miniapp_auth_v1", source: "loopback_preview" },
      cards: [
        {
          schema_version: "review_card_v1",
          card_id: "card-1",
          profile_id: "jobs-fast",
          title: "Frontend Mini App contract",
          rating: "high",
          decision_status: "new",
          source_refs: [],
          item: { why: "Paid React work." },
          status: "pending",
          opportunity_status: "open",
          opportunity_updated_at: "2026-05-17T00:00:00Z",
          report_path: "output/jobs-fast/report.html",
          updated_at: "2026-05-17T00:00:00Z",
        },
      ],
    });

    expect(state.cards[0].report_path).toBe("output/jobs-fast/report.html");
  });

  it("falls back to empty cards for malformed Mini App state sections", () => {
    expect(sanitizeMiniAppReviewState({ auth: null, cards: "bad" })).toEqual({
      cards: [],
      schema_version: undefined,
    });
  });
});
