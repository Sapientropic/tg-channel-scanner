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

describe("Desk boundary contract fixtures", () => {
  it("sanitizes Desk action and source payloads without backend-only fields", () => {
    const contract = fixture as DeskBoundaryFixture;
    const picked = {
      desk_actions: sanitizeDeskActions(contract.frontend_input.desk_actions),
      desk_action_result: sanitizeDeskActionResult(contract.frontend_input.desk_action_result),
      desk_sources: sanitizeDeskSourcesResult(contract.frontend_input.desk_sources),
    };
    const surfaced = JSON.stringify(picked);

    expect(picked).toEqual(contract.frontend_expected);
    for (const denied of contract.denied_strings) {
      expect(surfaced).not.toContain(denied);
    }
  });
});
