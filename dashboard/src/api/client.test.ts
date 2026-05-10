import { describe, expect, it } from "vitest";

import { errorMessage, normalizeDashboardError } from "./client";

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
