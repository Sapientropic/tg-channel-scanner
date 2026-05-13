import { describe, expect, it } from "vitest";
import fixture from "../../../tests/fixtures/contracts/desk_source_access_health_v1.summary.json";

import { sanitizeDeskActionResult } from "./sanitize";

type DeskSourceAccessFixture = {
  frontend_action_result: unknown;
  frontend_expected: unknown;
  denied_strings: string[];
};

function asRecord(value: unknown): Record<string, unknown> {
  expect(value).toBeTypeOf("object");
  expect(value).not.toBeNull();
  return value as Record<string, unknown>;
}

function actionResultContract(value: unknown) {
  const record = asRecord(value);
  return {
    schema_version: record.schema_version,
    action_id: record.action_id,
    status: record.status,
    display_command: record.display_command,
    exit_code: record.exit_code,
    artifact_path: record.artifact_path,
  };
}

function sourceAccessContract(value: unknown) {
  const record = asRecord(value);
  return {
    schema_version: record.schema_version,
    source_count: record.source_count,
    checked_count: record.checked_count,
    accessible_count: record.accessible_count,
    quiet_count: record.quiet_count,
    inaccessible_count: record.inaccessible_count,
    truncated_count: record.truncated_count,
    reason_counts: record.reason_counts,
    probe_window_hours_min: record.probe_window_hours_min,
    probe_window_hours_max: record.probe_window_hours_max,
  };
}

function expectDisplayFields(value: unknown, keys: string[]) {
  const record = asRecord(value);
  for (const key of keys) {
    expect(record[key], key).toBeTypeOf("string");
    expect(String(record[key]).trim(), key).not.toHaveLength(0);
  }
}

describe("desk_source_access_health_v1 contract fixture", () => {
  it("keeps source-access action summaries aggregate-only", () => {
    const contract = fixture as DeskSourceAccessFixture;
    const result = sanitizeDeskActionResult(contract.frontend_action_result);
    const surfaced = JSON.stringify(result);
    const resultRecord = asRecord(result);
    const expectedRecord = asRecord(contract.frontend_expected);
    const sourceAccess = asRecord(resultRecord.source_access);
    const expectedSourceAccess = asRecord(expectedRecord.source_access);

    expect(actionResultContract(result)).toEqual(actionResultContract(contract.frontend_expected));
    expectDisplayFields(result, ["title", "detail", "next_action"]);
    expect(resultRecord.finished_at).toBeTypeOf("string");
    expect(sourceAccessContract(sourceAccess)).toEqual(sourceAccessContract(expectedSourceAccess));
    expect(sourceAccess.checked_at).toBeTypeOf("string");
    for (const denied of contract.denied_strings) {
      expect(surfaced).not.toContain(denied);
    }
  });
});
