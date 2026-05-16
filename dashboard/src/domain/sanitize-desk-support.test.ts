import { describe, expect, it } from "vitest";

import { sanitizeDeskSupportDiagnosticExportResult, sanitizeDeskSupportStatus } from "./sanitize";

describe("support diagnostics sanitizer", () => {
  it("keeps support paths and boundaries while dropping malformed rows", () => {
    const status = sanitizeDeskSupportStatus({
      schema_version: "desk_support_status_v1",
      app_data_root: "/Users/example/Library/Application Support/T-Sense",
      code_root: "/Applications/T-Sense.app/Contents/Resources",
      database_path: "/Users/example/Library/Application Support/T-Sense/.tgcs/tgcs.db",
      output_dir: "/Users/example/Library/Application Support/T-Sense/output",
      source_registry_path: "/Users/example/Library/Application Support/T-Sense/.tgcs/sources.json",
      telegram_config_dir: "/Users/example/Library/Application Support/T-Sense/.tgcs/telegram",
      desktop_log_path: "/Users/example/Library/Logs/T-Sense/desktop-backend.log",
      dashboard_url: "http://127.0.0.1:8766",
      platform: "macOS",
      checked_at: "2026-05-16T14:00:00Z",
      paths: [
        { label: "Local data", path: "/tmp/T-Sense", exists: true, detail: "Local state." },
        { label: "", path: "/tmp/bad", detail: "Missing label." },
      ],
      data_boundaries: [
        { label: "AI requests", detail: "Selected scan text can be sent out.", external: true },
        "bad",
      ],
      recovery: [
        { label: "Backend will not start", detail: "Check logs.", path: "/tmp/log.txt" },
        { label: "Bad row" },
      ],
      readiness: {
        schema_version: "desk_support_readiness_v1",
        status: "needs_user",
        ready_count: 2,
        total_count: 5,
        summary: "2/5 real-scan checks ready.",
        items: [
          { label: "Demo report", status: "ready", detail: "A local sample report is available." },
          {
            label: "Telegram login",
            status: "needs_user",
            detail: "Telegram is not fully authorized on this Mac yet.",
            next_action: "Finish Telegram setup.",
          },
          { label: "Bad row", status: "", detail: "Missing status." },
        ],
      },
      migration: {
        schema_version: "desk_support_migration_v1",
        status: "manual_required",
        detail: "Legacy project data was found.",
        next_action: "Pick a user-selected source folder before migrating.",
        legacy_locations: [
          { label: "Legacy reports", path: "/Users/example/project/output", exists: true, detail: "Old reports." },
          { label: "", path: "/tmp/bad", exists: true, detail: "Missing label." },
        ],
      },
    });

    expect(status).toMatchObject({
      schema_version: "desk_support_status_v1",
      paths: [{ label: "Local data", exists: true }],
      data_boundaries: [{ label: "AI requests", external: true }],
      recovery: [{ label: "Backend will not start", path: "/tmp/log.txt" }],
      readiness: {
        status: "needs_user",
        ready_count: 2,
        items: [
          { label: "Demo report", status: "ready" },
          { label: "Telegram login", next_action: "Finish Telegram setup." },
        ],
      },
      migration: {
        status: "manual_required",
        legacy_locations: [{ label: "Legacy reports", exists: true }],
      },
    });
  });

  it("rejects missing required support fields", () => {
    expect(sanitizeDeskSupportStatus({ schema_version: "desk_support_status_v1" })).toBeNull();
  });

  it("validates support diagnostic export results", () => {
    expect(
      sanitizeDeskSupportDiagnosticExportResult({
        schema_version: "desk_support_diagnostic_export_v1",
        output_path: "/Users/example/Library/Application Support/T-Sense/output/diagnostics/t-sense-support.json",
        exported_at: "2026-05-16T14:00:00Z",
      }),
    ).toMatchObject({
      schema_version: "desk_support_diagnostic_export_v1",
      output_path: "/Users/example/Library/Application Support/T-Sense/output/diagnostics/t-sense-support.json",
      exported_at: "2026-05-16T14:00:00Z",
    });
    expect(
      sanitizeDeskSupportDiagnosticExportResult({
        schema_version: "desk_support_diagnostic_export_v1",
        output_path: "",
        exported_at: "2026-05-16T14:00:00Z",
      }),
    ).toBeNull();
  });
});
