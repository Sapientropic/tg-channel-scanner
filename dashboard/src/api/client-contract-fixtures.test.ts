import { afterEach, describe, expect, it, vi } from "vitest";
import deskFixture from "../../../tests/fixtures/contracts/desk_boundary_v1.json";

import { loadDeskActions, loadDeskSources, runDeskAction } from "./client";

type DeskBoundaryFixture = {
  desk_actions: {
    actions: unknown[];
  };
  desk_action_result: Record<string, unknown>;
  desk_sources: unknown;
};

function mockJsonResponse(payload: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => new Response(JSON.stringify(payload), { status: 200, headers: { "Content-Type": "application/json" } })),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("dashboard API client contract fixtures", () => {
  it("accepts fixture-backed Desk actions without backend-only fields", async () => {
    const fixture = deskFixture as DeskBoundaryFixture;
    mockJsonResponse(fixture.desk_actions);

    await expect(loadDeskActions()).resolves.toEqual(fixture.desk_actions.actions);
  });

  it("accepts fixture-backed Desk source library responses", async () => {
    const fixture = deskFixture as DeskBoundaryFixture;
    mockJsonResponse({ sources: fixture.desk_sources });

    await expect(loadDeskSources()).resolves.toEqual(fixture.desk_sources);
  });

  it("accepts fixture-backed Desk action results and rejects action-id drift", async () => {
    const fixture = deskFixture as DeskBoundaryFixture;
    mockJsonResponse({
      result: {
        ...fixture.desk_action_result,
        finished_at: "2026-05-13T00:00:00Z",
      },
    });

    await expect(runDeskAction("monitor_jobs_dry_run")).resolves.toEqual({
      ...fixture.desk_action_result,
      finished_at: "2026-05-13T00:00:00Z",
    });

    mockJsonResponse({
      result: {
        ...fixture.desk_action_result,
        action_id: "sources_probe_access",
      },
    });

    await expect(runDeskAction("monitor_jobs_dry_run")).rejects.toThrow("Invalid Desk action response");
  });
});
