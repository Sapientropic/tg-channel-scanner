import { afterEach, describe, expect, it, vi } from "vitest";

import {
  errorMessage,
  detectDeskDeliveryChatId,
  loadDashboardState,
  loadDeskActions,
  loadDeskAiSettingsStatus,
  loadDeskSources,
  normalizeDashboardError,
  previewSourceAssistant,
  runDeskAction,
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
});
