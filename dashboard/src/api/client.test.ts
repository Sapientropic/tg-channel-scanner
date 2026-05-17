import { afterEach, describe, expect, it, vi } from "vitest";

import {
  checkGitUpdates,
  clearFeedbackDecisions,
  createProfileFromBrief,
  errorMessage,
  detectDeskDeliveryChatId,
  exportDeskSupportDiagnostics,
  exportFeedback,
  generateFeedbackProfileSuggestions,
  clearDeskNotificationToken,
  loadDashboardState,
  loadDeskActions,
  loadDeskAiSettingsStatus,
  loadDeskNotificationTokenStatus,
  loadDeskSources,
  loadDeskSchedulerStatus,
  loadDeskTelegramStatus,
  loadProfileTemplates,
  loadMiniAppState,
  normalizeDashboardError,
  postMiniAppReviewCardAction,
  postMiniAppStarterSources,
  previewProfileCoach,
  previewProfileFromBrief,
  previewSourceAssistant,
  pullLatestGit,
  runDeskAction,
  saveDeskNotificationToken,
  saveDeskTelegramCredentials,
  saveDeskDeliveryTarget,
  testDeskDeliveryTarget,
} from "./client";

function mockJsonResponse(payload: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(payload), { status: 200, headers: { "Content-Type": "application/json" } })),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("dashboard API errors", () => {
  it("turns generic server failures into local recovery guidance", () => {
    expect(normalizeDashboardError("Internal Server Error")).toBe(
      "Local dashboard API hit an internal error. Refresh once; if it repeats, restart Signal Desk.",
    );
    expect(normalizeDashboardError("HTTP 500")).toContain("restart Signal Desk");
  });

  it("turns network failures into a reachable next step", () => {
    expect(errorMessage(new TypeError("Failed to fetch"))).toBe(
      "Local dashboard API is unreachable. Start or restart Signal Desk, then refresh.",
    );
  });

  it("hides profile patch ids from stale clear errors", () => {
    const message = normalizeDashboardError("Profile patch is not applied: patch_6668d2c593f24130bb26a668bbc43755");

    expect(message).toBe("This profile suggestion is already cleared. Refreshing the list will hide it.");
    expect(message).not.toContain("patch_");
  });

  it("keeps specific validation errors readable", () => {
    expect(errorMessage(new Error("Use 1 to 8 topic tags."))).toBe("Use 1 to 8 topic tags.");
    expect(errorMessage(new Error("Invalid source library response"))).toBe(
      "Local dashboard API returned data this screen cannot read. Refresh once; if it repeats, restart Signal Desk.",
    );
  });
});

describe("dashboard API contract validation", () => {
  it("throws on malformed dashboard state payloads instead of sanitizing to empty state", async () => {
    mockJsonResponse({
      schema_version: "dashboard_state_v1",
      profiles: "bad",
      inbox: [],
      runs: [],
      delivery_targets: [],
      profile_patch_suggestions: [],
      source_stats: [],
      source_insights: [],
    });

    await expect(loadDashboardState()).rejects.toThrow("Invalid dashboard state response");
  });

  it("loads Mini App state with Telegram init data and sanitizes cards", async () => {
    vi.stubGlobal("Telegram", { WebApp: { initData: "query_id=abc&hash=signature" } });
    const fetchMock = vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            miniapp: {
              schema_version: "miniapp_review_state_v1",
              auth: { schema_version: "telegram_miniapp_auth_v1", source: "telegram", user_id: "123456" },
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
                  updated_at: "2026-05-17T00:00:00Z",
                },
              ],
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const state = await loadMiniAppState();

    expect(state.cards[0].card_id).toBe("card-1");
    expect(fetchMock).toHaveBeenCalledWith("/api/miniapp/state", {
      headers: { "X-Telegram-Init-Data": "query_id=abc&hash=signature" },
      signal: undefined,
    });
  });

  it("posts Mini App review actions to encoded card paths", async () => {
    vi.stubGlobal("Telegram", { WebApp: { initData: "init-data" } });
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ ok: true, card: {} }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await postMiniAppReviewCardAction("card:123", "follow_up", "Prefer budget.");

    expect(fetchMock).toHaveBeenCalledWith("/api/miniapp/review-cards/card%3A123/action", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Telegram-Init-Data": "init-data" },
      body: JSON.stringify({ action: "follow_up", note: "Prefer budget." }),
      signal: undefined,
    });
  });

  it("posts Mini App starter source imports with Telegram init data", async () => {
    vi.stubGlobal("Telegram", { WebApp: { initData: "init-data" } });
    const fetchMock = vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            result: {
              schema_version: "desk_source_import_result_v1",
              dry_run: false,
              written: true,
              topic: "jobs",
              added_count: 1,
              updated_count: 0,
              unchanged_count: 0,
              source_count: 1,
              registry_path: ".tgcs/sources.json",
              preview_sources: [{ label: "Remote Front-End Jobs", source_id: "telegram:remote_frontend_jobs" }],
              preview_truncated_count: 0,
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await postMiniAppStarterSources("jobs");

    expect(result.added_count).toBe(1);
    expect(fetchMock).toHaveBeenCalledWith("/api/miniapp/sources/starter", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Telegram-Init-Data": "init-data" },
      body: JSON.stringify({ topic: "jobs" }),
      signal: undefined,
    });
  });

  it("throws on malformed Desk actions payloads instead of returning no controls", async () => {
    mockJsonResponse({ schema_version: "desk_actions_v1", actions: "bad" });

    await expect(loadDeskActions()).rejects.toThrow("Invalid Desk actions response");
  });

  it("throws on schema-less source library payloads instead of accepting sanitizer fallback", async () => {
    mockJsonResponse({
      sources: {
        registry_path: ".tgcs/sources.json",
        source_count: 0,
        enabled_count: 0,
        topics: [],
        sources: [],
      },
    });

    await expect(loadDeskSources()).rejects.toThrow("Invalid source library response");
  });

  it("throws on schema-less source assistant payloads instead of accepting sanitizer fallback", async () => {
    mockJsonResponse({
      result: {
        dry_run: true,
        written: false,
        topic: "jobs",
        registry_path: ".tgcs/sources.json",
        preview_sources: [],
        resolved_plan: { add: [], remove: [], disable: [], enable: [] },
      },
    });

    await expect(previewSourceAssistant("add @remote_jobs", "jobs")).rejects.toThrow("Invalid source assistant response");
  });

  it("passes Telegram folder id through source assistant discovery requests", async () => {
    const fetchMock = vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            result: {
              schema_version: "desk_source_import_result_v1",
              dry_run: true,
              written: false,
              action: "assistant",
              topic: "jobs",
              added_count: 0,
              updated_count: 0,
              unchanged_count: 0,
              source_count: 0,
              registry_path: ".tgcs/sources.json",
              preview_sources: [],
              preview_truncated_count: 0,
              resolved_plan: { add: [], remove: [], disable: [], enable: [] },
            },
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await previewSourceAssistant("scan folder", "jobs", true, "jobs-fast", "Jobs", "12");

    expect(fetchMock).toHaveBeenCalledWith("/api/desk/sources/assistant", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        instruction: "scan folder",
        topic: "jobs",
        dry_run: true,
        confirm_external_ai: true,
        profile_id: "jobs-fast",
        folder_name: "Jobs",
        folder_id: "12",
      }),
      signal: undefined,
    });
  });

  it("throws on schema-less delivery target payloads instead of accepting sanitizer fallback", async () => {
    mockJsonResponse({
      target: {
        target_id: "telegram-bot-default",
        type: "telegram_bot",
        enabled: true,
        config: { chat_id: "123456" },
        updated_at: "2026-05-10T00:00:00Z",
      },
    });

    await expect(saveDeskDeliveryTarget("telegram-bot-default", "123456", true)).rejects.toThrow(
      "Invalid notification target response",
    );
  });

  it("throws on empty AI settings payloads instead of rendering an unconfigured state", async () => {
    mockJsonResponse({ ai: {} });

    await expect(loadDeskAiSettingsStatus()).rejects.toThrow("Invalid AI API settings response");
  });

  it("throws on incomplete AI settings payloads with only a schema version", async () => {
    mockJsonResponse({ ai: { schema_version: "desk_ai_settings_status_v1" } });

    await expect(loadDeskAiSettingsStatus()).rejects.toThrow("Invalid AI API settings response");
  });

  it("throws on schema-less status payloads instead of rendering fallback scheduler, token, or Telegram state", async () => {
    mockJsonResponse({
      scheduler: {
        available: true,
        installed: false,
        status: "not_installed",
        task_label: "jobs-fast dry-run",
        interval_minutes: 15,
        detail: "Background scan is off.",
        next_action: "Install scheduler.",
        checked_at: "2026-05-13T00:00:00Z",
      },
    });

    await expect(loadDeskSchedulerStatus()).rejects.toThrow("Invalid scheduler status response");

    mockJsonResponse({
      token: {
        configured: false,
        source: "missing",
        env_configured: false,
        local_store_supported: true,
        local_store_configured: false,
        can_save: true,
        can_clear: false,
        platform: "win32",
        detail: "Telegram bot token is not configured.",
      },
    });

    await expect(loadDeskNotificationTokenStatus()).rejects.toThrow("Invalid notification token response");

    mockJsonResponse({
      telegram: {
        credentials_ready: true,
        session_ready: false,
        login_state: "ready_for_code",
        detail: "Credentials are saved.",
        next_step: "Send a code.",
        config_path: "~/.config/tgcli/config.toml",
        session_path: "~/.config/tgcli/session",
      },
    });

    await expect(loadDeskTelegramStatus()).rejects.toThrow("Invalid Telegram status response");
  });

  it("throws on schema-less notification token and Telegram mutation responses", async () => {
    mockJsonResponse({
      token: {
        configured: true,
        source: "local_keyring",
        env_configured: false,
        local_store_supported: true,
        local_store_configured: true,
        can_save: true,
        can_clear: true,
        platform: "win32",
        detail: "Telegram bot token is saved locally.",
      },
    });

    await expect(saveDeskNotificationToken("bot-token")).rejects.toThrow("Invalid notification token response");

    mockJsonResponse({
      token: {
        schema_version: "desk_notification_token_status_v1",
        configured: false,
        source: "missing",
        env_configured: false,
        local_store_supported: true,
        local_store_configured: false,
        can_save: true,
        can_clear: false,
        platform: "",
        detail: "Telegram bot token is not configured.",
      },
    });

    await expect(clearDeskNotificationToken()).rejects.toThrow("Invalid notification token response");

    mockJsonResponse({
      telegram: {
        credentials_ready: true,
        session_ready: false,
        login_state: "code_sent",
        detail: "Telegram sent a verification code.",
        next_step: "Enter the code.",
        config_path: "~/.config/tgcli/config.toml",
        session_path: "~/.config/tgcli/session",
      },
    });

    await expect(saveDeskTelegramCredentials("123", "hash")).rejects.toThrow("Invalid Telegram credentials response");
  });

  it("throws on schema-less Desk action results instead of accepting sanitizer fallback", async () => {
    mockJsonResponse({
      result: {
        action_id: "monitor_jobs_dry_run",
        status: "success",
        title: "Practice scan finished",
        display_command: "tgcs monitor run --profile-id jobs-fast --delivery-mode dry-run",
      },
    });

    await expect(runDeskAction("monitor_jobs_dry_run")).rejects.toThrow("Invalid Desk action response");
  });

  it("throws when a Desk action result belongs to another action", async () => {
    mockJsonResponse({
      result: {
        schema_version: "desk_action_result_v1",
        action_id: "feedback_export",
        status: "success",
        title: "Exported feedback",
        display_command: "tgcs feedback export",
      },
    });

    await expect(runDeskAction("monitor_jobs_dry_run")).rejects.toThrow("Invalid Desk action response");
  });

  it("throws on schema-less delivery test results", async () => {
    mockJsonResponse({
      result: {
        target_id: "telegram-bot-default",
        target_type: "telegram_bot",
        ok: true,
        status: "dry_run",
      },
    });

    await expect(testDeskDeliveryTarget("telegram-bot-default", "123456")).rejects.toThrow(
      "Invalid notification test response",
    );
  });

  it("throws when a delivery test result belongs to another target", async () => {
    mockJsonResponse({
      result: {
        schema_version: "desk_delivery_test_result_v1",
        target_id: "other-target",
        target_type: "telegram_bot",
        ok: true,
        status: "dry_run",
      },
    });

    await expect(testDeskDeliveryTarget("telegram-bot-default", "123456")).rejects.toThrow(
      "Invalid notification test response",
    );
  });

  it("throws on schema-less chat detection results", async () => {
    mockJsonResponse({
      result: {
        target_id: "telegram-bot-default",
        target_type: "telegram_bot",
        ok: true,
        status: "detected",
        source: "updates",
      },
    });

    await expect(detectDeskDeliveryChatId("telegram-bot-default")).rejects.toThrow(
      "Invalid notification chat detection response",
    );
  });

  it("throws when a chat detection result belongs to another target", async () => {
    mockJsonResponse({
      result: {
        schema_version: "desk_delivery_chat_detection_v1",
        target_id: "other-target",
        target_type: "telegram_bot",
        ok: true,
        status: "detected",
        source: "updates",
      },
    });

    await expect(detectDeskDeliveryChatId("telegram-bot-default")).rejects.toThrow(
      "Invalid notification chat detection response",
    );
  });

  it("throws on schema-less Git mutation results instead of accepting status-shaped payloads", async () => {
    mockJsonResponse({
      git: {
        status: "behind",
        message: "1 upstream commit available.",
        branch: "main",
        ahead: 0,
        behind: 1,
        dirty: false,
        dirty_count: 0,
        pull_allowed: true,
        checked_at: "2026-05-13T00:00:00Z",
      },
    });

    await expect(checkGitUpdates()).rejects.toThrow("Invalid git status response");

    mockJsonResponse({
      git: {
        schema_version: "git_update_status_v0",
        status: "up_to_date",
        message: "Local branch is up to date.",
        branch: "main",
        ahead: 0,
        behind: 0,
        dirty: false,
        dirty_count: 0,
        pull_allowed: false,
        checked_at: "2026-05-13T00:00:00Z",
      },
    });

    await expect(pullLatestGit()).rejects.toThrow("Invalid git status response");
  });

  it("throws on schema-less feedback mutation results instead of accepting plausible counters", async () => {
    mockJsonResponse({
      export: {
        feedback_count: 1,
        output_path: "output/feedback/review-feedback.jsonl",
      },
    });

    await expect(exportFeedback()).rejects.toThrow("Invalid feedback export response");

    mockJsonResponse({
      suggestions: {
        created_count: 1,
        existing_count: 0,
        skipped_count: 0,
      },
    });

    await expect(generateFeedbackProfileSuggestions()).rejects.toThrow(
      "Invalid feedback profile suggestions response",
    );

    mockJsonResponse({
      feedback: {
        schema_version: "feedback_clear_result_v1",
        cleared_count: -1,
      },
    });

    await expect(clearFeedbackDecisions()).rejects.toThrow("Invalid feedback clear response");
  });

  it("validates support diagnostic export responses", async () => {
    mockJsonResponse({
      support: {
        schema_version: "desk_support_diagnostic_export_v1",
        output_path: "/Users/example/Library/Application Support/T-Sense/output/diagnostics/t-sense-support.json",
        exported_at: "2026-05-16T14:00:00Z",
      },
    });

    await expect(exportDeskSupportDiagnostics()).resolves.toMatchObject({
      schema_version: "desk_support_diagnostic_export_v1",
      output_path: "/Users/example/Library/Application Support/T-Sense/output/diagnostics/t-sense-support.json",
    });

    mockJsonResponse({
      support: {
        output_path: "/Users/example/Library/Application Support/T-Sense/output/diagnostics/t-sense-support.json",
      },
    });

    await expect(exportDeskSupportDiagnostics()).rejects.toThrow("Invalid support diagnostic export response");
  });

  it("throws on schema-less profile creation results instead of trusting profile-shaped payloads", async () => {
    mockJsonResponse({
      profile: {
        profile_id: "jobs-fast",
        display_name: "Jobs Fast",
        profile_path: "profiles/jobs-fast.md",
        created: true,
        detail: "Created profile.",
        next_action: "Review the draft.",
      },
    });

    await expect(createProfileFromBrief({ brief: "Track remote TypeScript roles." })).rejects.toThrow(
      "Invalid profile creation response",
    );
  });

  it("validates profile template, create preview, and coach preview responses", async () => {
    mockJsonResponse({
      templates: {
        schema_version: "desk_profile_template_catalog_v1",
        templates: [
          {
            id: "jobs",
            title: "Developer opportunities",
            audience: "Developers",
            default_topic: "jobs",
            starter_brief: "Track paid developer work.",
            coach_questions: ["Must have?"],
            supported_fields: ["search_rules", "rejection_rules"],
          },
        ],
      },
    });

    await expect(loadProfileTemplates()).resolves.toEqual({
      schema_version: "desk_profile_template_catalog_v1",
      templates: [
        {
          id: "jobs",
          title: "Developer opportunities",
          audience: "Developers",
          default_topic: "jobs",
          starter_brief: "Track paid developer work.",
          coach_questions: ["Must have?"],
          supported_fields: ["search_rules", "rejection_rules"],
        },
      ],
    });

    mockJsonResponse({
      preview: {
        schema_version: "desk_profile_create_preview_v1",
        status: "ready",
        template_id: "jobs",
        title: "Developer opportunities",
        topic: "jobs",
        questions: [],
        generated_rules: ["Include paid TypeScript work."],
        search_rules: ["Include paid TypeScript work."],
        rejection_rules: ["Reject unpaid internships."],
        keywords: ["typescript"],
        markdown_preview: "# Profile",
        warnings: [],
        llm_used: true,
      },
    });

    await expect(previewProfileFromBrief({ brief: "Track TypeScript work.", template_id: "jobs" })).resolves.toMatchObject({
      schema_version: "desk_profile_create_preview_v1",
      status: "ready",
      template_id: "jobs",
    });

    mockJsonResponse({
      coach: {
        schema_version: "profile_coach_preview_v1",
        status: "ready",
        profile_id: "jobs-fast",
        evidence_counts: { keep: 1, skip: 0, false_positive: 1, follow_up: 1 },
        diagnosis: [{ label: "Wrong matches", detail: "Tighten exclusions." }],
        suspected_false_positive_patterns: ["full-stack generalists"],
        suggested_preference_rules: ["Exclude full-stack roles."],
        source_suggestions: [],
        confidence: "medium",
        warnings: [],
        llm_used: true,
      },
    });

    await expect(previewProfileCoach("jobs-fast")).resolves.toMatchObject({
      schema_version: "profile_coach_preview_v1",
      profile_id: "jobs-fast",
      suggested_preference_rules: ["Exclude full-stack roles."],
    });
  });
});
