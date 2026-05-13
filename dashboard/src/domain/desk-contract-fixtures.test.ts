import { describe, expect, it } from "vitest";
import fixture from "../../../tests/fixtures/contracts/desk_boundary_v1.json";

import { sanitizeDeskActions, sanitizeDeskActionResult, sanitizeDeskSourcesResult } from "./sanitize";

type DeskBoundaryFixture = {
  frontend_input: {
    desk_actions: unknown;
    desk_action_result: unknown;
    desk_sources: unknown;
  };
  frontend_expected: {
    desk_actions: unknown;
    desk_action_result: unknown;
    desk_sources: unknown;
  };
  denied_strings: string[];
};

function asRecord(value: unknown): Record<string, unknown> {
  expect(value).toBeTypeOf("object");
  expect(value).not.toBeNull();
  return value as Record<string, unknown>;
}

function deskActionContract(value: unknown) {
  const record = asRecord(value);
  return {
    schema_version: record.schema_version,
    action_id: record.action_id,
    group: record.group,
    run_mode: record.run_mode,
    display_command: record.display_command,
  };
}

function deskActionResultContract(value: unknown) {
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

function expectDisplayFields(value: unknown, keys: string[]) {
  const record = asRecord(value);
  for (const key of keys) {
    expect(record[key], key).toBeTypeOf("string");
    expect(String(record[key]).trim(), key).not.toHaveLength(0);
  }
}

describe("Desk boundary contract fixtures", () => {
  it("sanitizes Desk action and source payloads without backend-only fields", () => {
    const contract = fixture as DeskBoundaryFixture;
    const picked = {
      desk_actions: sanitizeDeskActions(contract.frontend_input.desk_actions),
      desk_action_result: sanitizeDeskActionResult(contract.frontend_input.desk_action_result),
      desk_sources: sanitizeDeskSourcesResult(contract.frontend_input.desk_sources),
    };
    const surfaced = JSON.stringify(picked);

    const expected = contract.frontend_expected as Record<string, unknown>;
    const actualActions = picked.desk_actions;
    const expectedActions = expected.desk_actions as unknown[];
    expect(actualActions).toHaveLength(expectedActions.length);
    expect(actualActions.map(deskActionContract)).toEqual(expectedActions.map(deskActionContract));
    for (const action of actualActions) {
      expectDisplayFields(action, ["title", "detail", "next_action"]);
    }

    expect(deskActionResultContract(picked.desk_action_result)).toEqual(
      deskActionResultContract(expected.desk_action_result),
    );
    expectDisplayFields(picked.desk_action_result, ["title", "detail", "next_action"]);
    expect(asRecord(picked.desk_action_result).finished_at).toBeTypeOf("string");

    expect(picked.desk_sources).toEqual(expected.desk_sources);
    for (const denied of contract.denied_strings) {
      expect(surfaced).not.toContain(denied);
    }
  });
});
