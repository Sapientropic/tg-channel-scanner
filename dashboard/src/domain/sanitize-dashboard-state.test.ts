import { afterEach, describe, expect, it, vi } from "vitest";

import {
  emptyDashboardState,
  sanitizeDashboardState,
  sanitizeInboxCards,
} from "./sanitize";

const validCard = {
  schema_version: "review_card_v1" as const,
  card_id: "card-1",
  profile_id: "jobs-fast",
  title: "Frontend role",
  rating: "high",
  decision_status: "new",
  opportunity_status: "open",
  opportunity_updated_at: "",
  source_refs: [],
  item: {},
  status: "pending",
  updated_at: "2026-05-09T00:00:00Z",
};

describe("dashboard state sanitizers", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("falls back to empty arrays for malformed state sections", () => {
    expect(sanitizeDashboardState({ inbox: "bad" as never, runs: null as never })).toEqual({
      ...emptyDashboardState,
      schema_version: undefined,
    });
  });

  it("drops malformed optional object sections instead of passing null or arrays through", () => {
    expect(
      sanitizeDashboardState({
        schema_version: "bad" as never,
        feedback_summary: null as never,
        opportunity_summary: [] as never,
        validation_summary: "bad" as never,
        setup_status: { stage: "ready" },
      }),
    ).toEqual({
      ...emptyDashboardState,
      setup_status: { stage: "ready" },
      schema_version: undefined,
    });
  });

  it("filters malformed dashboard array elements before they reach view code", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const state = sanitizeDashboardState({
      profiles: [null, { profile_id: "jobs-fast", enabled: true, updated_at: "2026-05-09T00:00:00Z" }],
      runs: [{ run_id: "run-1", profile_id: "jobs-fast" }, { run_id: "run-2", profile_id: "jobs-fast", status: "complete", started_at: "2026-05-09T00:00:00Z" }],
      source_stats: [{ channel: "jobs", high_count: 2, scan_failure_reason: " permission_or_private " }],
      source_insights: [{ channel: "jobs", label: "Watch", reason: "Thin source", stats: { channel: "jobs" } }],
    });
    expect(state.profiles).toEqual([{ profile_id: "jobs-fast", enabled: true, updated_at: "2026-05-09T00:00:00Z" }]);
    expect(state.runs).toEqual([{ run_id: "run-2", profile_id: "jobs-fast", status: "complete", started_at: "2026-05-09T00:00:00Z" }]);
    expect(state.source_stats[0]).toMatchObject({ channel: "jobs", card_count: 0, high_count: 2, high_rate: 0, scan_failure_reason: "permission_or_private" });
    expect(state.source_insights[0].stats).toMatchObject({ channel: "jobs", card_count: 0 });
    expect(warn).toHaveBeenCalledWith("[tgcs dashboard schema] profiles[0] expected object", null);
    expect(warn).toHaveBeenCalledWith("[tgcs dashboard schema] runs[0].status expected non-empty string", undefined);
  });

  it("keeps profile schedule and alert rule runtime fields without exposing raw config", () => {
    const state = sanitizeDashboardState({
      profiles: [
        {
          profile_id: "jobs-fast",
          enabled: true,
          alert_schedule_mode: "work_hours",
          scan_window_hours: 6,
          semantic_max_messages: 40,
          timezone: "America/New_York",
          workdays: ["mon", "wed", "fri", 7],
          work_start: "08:30",
          work_end: "18:15",
          work_interval_minutes: 30,
          off_hours_interval_minutes: 120,
          alert_rule: "high_new_only",
          alert_max_age_minutes: 45,
          updated_at: "2026-05-13T00:00:00Z",
          config: { token: "secret" },
        },
      ],
    });

    expect(state.profiles[0]).toEqual({
      profile_id: "jobs-fast",
      enabled: true,
      alert_schedule_mode: "work_hours",
      scan_window_hours: 6,
      semantic_max_messages: 40,
      timezone: "America/New_York",
      workdays: ["mon", "wed", "fri"],
      work_start: "08:30",
      work_end: "18:15",
      work_interval_minutes: 30,
      off_hours_interval_minutes: 120,
      alert_rule: "high_new_only",
      alert_max_age_minutes: 45,
      updated_at: "2026-05-13T00:00:00Z",
    });
    expect(JSON.stringify(state)).not.toContain("secret");
  });

  it("sanitizes active Desk action progress from dashboard state", () => {
    const state = sanitizeDashboardState({
      active_actions: [
        {
          schema_version: "desk_active_action_v1",
          action_id: "sources_probe_access",
          title: "Check source access",
          status: "running",
          started_at: "2026-05-12T15:00:00Z",
          updated_at: "2026-05-12T15:01:00Z",
          elapsed_seconds: 61,
          checked_count: 17,
          total_count: 68,
          detail: "Source access check running; checked 17/68 sources.",
        },
        { action_id: "", title: "bad", status: "running", started_at: "" },
      ],
    });

    expect(state.active_actions).toEqual([
      {
        schema_version: "desk_active_action_v1",
        action_id: "sources_probe_access",
        title: "Check source access",
        status: "running",
        started_at: "2026-05-12T15:00:00Z",
        updated_at: "2026-05-12T15:01:00Z",
        elapsed_seconds: 61,
        checked_count: 17,
        total_count: 68,
        detail: "Source access check running; checked 17/68 sources.",
      },
    ]);
  });

  it("keeps structured source access summaries on setup checks", () => {
    const state = sanitizeDashboardState({
      setup_status: {
        stage: "needs_source_access",
        checks: [
          {
            check_id: "source_access",
            label: "Source access",
            status: "blocked",
            detail: "Access check: 2 recently active.",
            source_access: {
              schema_version: "desk_source_access_health_v1",
              source_count: 8,
              checked_count: 8,
              accessible_count: 2,
              quiet_count: 1,
              inaccessible_count: 5,
              truncated_count: 0,
              probe_window_hours: 24,
            },
          },
        ],
      },
    });

    expect(state.setup_status?.checks?.[0].source_access).toMatchObject({
      accessible_count: 2,
      quiet_count: 1,
      inaccessible_count: 5,
      probe_window_hours: 24,
    });
  });

  it("keeps safe source ref urls and drops unsafe ones", () => {
    expect(
      sanitizeInboxCards([
        {
          ...validCard,
          source_refs: [
            { channel: "jobs", id: 1, url: "https://t.me/jobs/1" },
            { channel: "bad", id: 2, url: "javascript:alert(1)" },
          ],
        },
      ])[0].source_refs,
    ).toEqual([
      { channel: "jobs", id: 1, url: "https://t.me/jobs/1" },
      { channel: "bad", id: 2 },
    ]);
  });

  it("sanitizes nested run quality fields before diagnostic formatting", () => {
    const state = sanitizeDashboardState({
      runs: [
        {
          run_id: "run-1",
          profile_id: "jobs-fast",
          status: "complete",
          started_at: "2026-05-09T00:00:00Z",
          quality: {
            semantic_stage: 12,
            top_diagnostic_code: {},
            cache_hit_rate: null,
            latency_ms: 100,
            completion_tokens: Number.POSITIVE_INFINITY,
            diagnostic_count: 1,
            diagnostic_failure_count: Number.NaN,
            diagnostic_warning_count: Number.NEGATIVE_INFINITY,
          },
        },
      ],
    });
    expect(state.runs[0].quality).toEqual({ cache_hit_rate: null, latency_ms: 100, diagnostic_count: 1 });
  });

  it("preserves explicit null run artifacts but omits malformed artifacts", () => {
    const state = sanitizeDashboardState({
      runs: [
        {
          run_id: "run-null",
          profile_id: "jobs-fast",
          status: "complete",
          started_at: "2026-05-09T00:00:00Z",
          report_artifact: null,
        },
        {
          run_id: "run-missing",
          profile_id: "jobs-fast",
          status: "complete",
          started_at: "2026-05-09T00:00:00Z",
        },
        {
          run_id: "run-bad",
          profile_id: "jobs-fast",
          status: "complete",
          started_at: "2026-05-09T00:00:00Z",
          report_artifact: { path: 42 },
        },
        {
          run_id: "run-absolute",
          profile_id: "jobs-fast",
          status: "complete",
          started_at: "2026-05-09T00:00:00Z",
          report_artifact: { path: "C:/Users/Administrator/private/report.html" },
        },
        {
          run_id: "run-traversal",
          profile_id: "jobs-fast",
          status: "complete",
          started_at: "2026-05-09T00:00:00Z",
          report_artifact: { path: "output/runs/run-1/../secret-report.html" },
        },
        {
          run_id: "run-non-report",
          profile_id: "jobs-fast",
          status: "complete",
          started_at: "2026-05-09T00:00:00Z",
          report_artifact: { path: "output/runs/run-1/scan.jsonl" },
        },
        {
          run_id: "run-report",
          profile_id: "jobs-fast",
          status: "complete",
          started_at: "2026-05-09T00:00:00Z",
          report_artifact: { path: "output/runs/run-1/jobs-fast-signal-report-2026-05-09-1225.html" },
        },
      ],
    });
    expect(state.runs[0]).toHaveProperty("report_artifact", null);
    expect(state.runs[1]).not.toHaveProperty("report_artifact");
    expect(state.runs[2]).not.toHaveProperty("report_artifact");
    expect(state.runs[3]).not.toHaveProperty("report_artifact");
    expect(state.runs[4]).not.toHaveProperty("report_artifact");
    expect(state.runs[5]).not.toHaveProperty("report_artifact");
    expect(state.runs[6].report_artifact?.path).toBe("output/runs/run-1/jobs-fast-signal-report-2026-05-09-1225.html");
  });

  it("drops empty optional summary objects", () => {
    expect(
      sanitizeDashboardState({
        feedback_summary: {},
        opportunity_summary: {},
        validation_summary: {},
        setup_status: {},
      }),
    ).toEqual({ ...emptyDashboardState, schema_version: undefined });
  });

  it("sanitizes optional dashboard summary sections instead of trusting objects", () => {
    const state = sanitizeDashboardState({
      delivery_targets: [
        {
          target_id: "legacy-target",
          type: "telegram_bot",
          enabled: true,
          config: { chat_id: "999999", bot_token: "secret" },
          updated_at: "2026-05-10T00:00:00Z",
        },
        {
          schema_version: "delivery_target_v1",
          target_id: "telegram-bot-default",
          type: "telegram_bot",
          enabled: true,
          config: {
            chat_id: "123456",
            bot_token: "secret",
            token: "secret",
            mode: "live",
          },
          updated_at: "2026-05-10T00:00:00Z",
        },
      ],
      opportunity_summary: {
        status: "failed",
        diagnostics: "bad",
        decision_counts: { new: 2, bad: "x", infinite: Number.POSITIVE_INFINITY },
        next_action: { label: "Fix sources", command: 12, target: "inbox" },
        top_items: [{ card_id: "card-1", title: "Role", rating: "high", decision_status: "new", status: "pending", source_refs: ["bad"] }],
      },
      validation_summary: { by_action: { keep: 1, skip: "bad", bad_nan: Number.NaN }, next_action: { detail: "Review outcomes" } },
      feedback_summary: {
        recent_impacts: ["bad", {}, { item_title: "Kept role", impact_status: 3 }],
        by_rating: { high: 1, low: null },
        last_export_path: "C:/Users/Administrator/private/review-feedback.jsonl",
      },
      setup_status: { checks: [{ check_id: "profiles", label: "Profiles", status: "active", command: 42 }, null] },
    });
    expect(state.opportunity_summary).toEqual({
      status: "failed",
      decision_counts: { new: 2 },
      next_action: { label: "Fix sources", target: "inbox" },
      top_items: [{ card_id: "card-1", title: "Role", rating: "high", decision_status: "new", status: "pending", source_refs: [] }],
    });
    expect(state.validation_summary).toEqual({ by_action: { keep: 1 }, next_action: { detail: "Review outcomes" } });
    expect(state.feedback_summary).toEqual({ recent_impacts: [{ item_title: "Kept role" }], by_rating: { high: 1 } });
    expect(
      sanitizeDashboardState({ feedback_summary: { last_export_path: " output\\feedback\\review-feedback.jsonl " } }).feedback_summary
        ?.last_export_path,
    ).toBe("output/feedback/review-feedback.jsonl");
    expect(state.setup_status).toEqual({ checks: [{ check_id: "profiles", label: "Profiles", status: "active" }] });
    expect(state.delivery_targets).toHaveLength(1);
    expect(state.delivery_targets[0].config).toEqual({ chat_id: "123456" });
    expect(JSON.stringify(state.delivery_targets)).not.toContain("secret");
  });

  it("sanitizes nested optional objects instead of object-level casting", () => {
    const state = sanitizeDashboardState({
      profile_patch_suggestions: [
        {
          patch_id: "patch-1",
          profile_id: "jobs-fast",
          note: "Retune threshold",
          status: "pending",
          diff_text: "{}",
          created_at: "2026-05-09T00:00:00Z",
          apply_readiness: { status: 1, label: "Ready", detail: null, extra: "ignored" },
        },
      ],
      source_insights: [
        {
          channel: "jobs",
          label: "Watch jobs",
          reason: "Good yield",
          next_action: { label: "Review source", command: 7, target: "ignored" },
        },
      ],
      inbox: [
        {
          ...validCard,
          item: {
            why: "Strong match",
            decision_state: {
              status: "new",
              signals: ["salary", "   ", 2],
              explanations: { salary: "clear", blank: "", whitespace: " ", bad: 3 },
              extra: "ignored",
            },
          },
        },
        {
          ...validCard,
          card_id: "card-empty-decision-state",
          item: { decision_state: { signals: [], explanations: {} } },
        },
      ],
    });
    expect(state.profile_patch_suggestions[0].apply_readiness).toEqual({ label: "Ready" });
    expect(state.source_insights[0].next_action).toEqual({ label: "Review source" });
    expect(state.inbox[0].item).toEqual({
      why: "Strong match",
      decision_state: { status: "new", signals: ["salary"], explanations: { salary: "clear" } },
    });
    expect(state.inbox[1].item).toEqual({});
  });

  it("drops nested optional objects when every known field is invalid", () => {
    const state = sanitizeDashboardState({
      profile_patch_suggestions: [
        {
          patch_id: "patch-1",
          profile_id: "jobs-fast",
          note: "Retune threshold",
          status: "pending",
          diff_text: "{}",
          created_at: "2026-05-09T00:00:00Z",
          apply_readiness: { status: 1, label: "", detail: [] },
        },
      ],
      source_insights: [
        {
          channel: "jobs",
          label: "Watch jobs",
          reason: "Good yield",
          next_action: { label: "", command: 7, detail: null },
        },
      ],
    });
    expect(state.profile_patch_suggestions[0].apply_readiness).toBeUndefined();
    expect(state.source_insights[0].next_action).toBeUndefined();
  });

  it("filters non-object inbox entries instead of casting them through", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const cards = sanitizeInboxCards([validCard, null, "bad", {}]);
    expect(cards).toEqual([validCard]);
    expect(warn).toHaveBeenCalledWith("[tgcs dashboard schema] inbox[1] expected object", null);
    expect(warn).toHaveBeenCalledWith("[tgcs dashboard schema] inbox[2] expected object", "bad");
    expect(warn).toHaveBeenCalledWith("[tgcs dashboard schema] inbox[3].card_id expected non-empty string", undefined);
  });

  it("keeps object cards renderable while warning on unexpected field types", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const dirtyCard = { ...validCard, card_id: "card-2", rating: 0, decision_status: false };
    const cards = sanitizeInboxCards([dirtyCard]);
    expect(cards).toEqual([{ ...validCard, card_id: "card-2", rating: "unknown", decision_status: "unknown" }]);
    expect(warn).toHaveBeenCalledWith("[tgcs dashboard schema] inbox[0].rating expected string/null/undefined", 0);
    expect(warn).toHaveBeenCalledWith("[tgcs dashboard schema] inbox[0].decision_status expected string/null/undefined", false);
  });

  it("builds a safe review card shape instead of trusting extra backend fields", () => {
    const card = {
      ...validCard,
      extra: "ignored",
      item: { why: "Strong match", decision_state: { status: "new" } },
      source_refs: [{ channel: "jobs", id: 1 }, { channel: "bad" }, "bad"],
    };
    expect(sanitizeInboxCards([card])).toEqual([
      {
        ...validCard,
        item: { why: "Strong match", decision_state: { status: "new" } },
        source_refs: [{ channel: "jobs", id: 1 }],
      },
    ]);
  });
});
