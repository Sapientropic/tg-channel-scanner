import { describe, expect, it } from "vitest";

import { sanitizeSourceImportResult } from "./sanitize";
import { sanitizeSourceImportResult as sanitizeDashboardModuleSourceImportResult } from "./sanitize/dashboard";
import { sanitizeSourceImportResult as sanitizeDeskModuleSourceImportResult } from "./sanitize/desk";
import sourceImportFixture from "../../../tests/fixtures/contracts/desk_source_import_result_v1.json";

describe("sanitizer entrypoint compatibility", () => {
  it("keeps source import result semantics aligned across public and legacy sanitizer entrypoints", () => {
    const expected = {
      schema_version: "desk_source_import_result_v1",
      dry_run: true,
      written: false,
      topic: "jobs",
      added_count: 2,
      updated_count: 1,
      unchanged_count: 0,
      removed_count: 3,
      enabled_count: 4,
      disabled_count: 5,
      source_count: 14,
      registry_path: ".tgcs/sources.json",
      preview_sources: [{ label: "remote_jobs", source_id: "telegram:remote_jobs" }],
      resolved_plan: {
        add: ["remote_jobs"],
        remove: ["telegram:old_jobs"],
        disable: ["telegram:spam_jobs"],
        enable: ["telegram:paused_jobs"],
      },
      preview_truncated_count: 1,
      action: "assistant_apply",
      llm_used: true,
      title: "Source plan ready",
      detail: "Review first.",
      next_action: "Apply reviewed changes.",
      finished_at: "2026-05-13T00:00:00Z",
    };

    expect(sanitizeSourceImportResult(sourceImportFixture)).toEqual(expected);
    expect(sanitizeDeskModuleSourceImportResult(sourceImportFixture)).toEqual(expected);
    expect(sanitizeDashboardModuleSourceImportResult(sourceImportFixture)).toEqual(expected);
    expect(JSON.stringify(sanitizeSourceImportResult(sourceImportFixture))).not.toContain("SECRET_SHOULD_NOT_RENDER");
  });
});
