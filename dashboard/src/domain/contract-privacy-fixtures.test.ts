import { describe, expect, it } from "vitest";
import fixture from "../../../tests/fixtures/contracts/review-card-privacy-item.json";

import { sanitizeDashboardState } from "./sanitize";

type ContractPrivacyFixture = {
  dashboard_state: unknown;
  denied_strings: string[];
};

describe("shared contract privacy fixtures", () => {
  it("keeps raw text, secrets, local paths, argv, and unsafe URLs out of dashboard state", () => {
    const contract = fixture as ContractPrivacyFixture;
    const state = sanitizeDashboardState(contract.dashboard_state);
    const surfaced = JSON.stringify(state);

    expect(state.inbox[0]?.title).toBe("Senior TypeScript Engineer - ACME Labs");
    expect(state.inbox[0]?.item.why).toBe("Strong TypeScript and React match.");
    expect(state.inbox[0]?.source_refs[0]?.url).toBe("https://t.me/jobs/42");
    expect(state.delivery_targets[0]?.config).toEqual({ chat_id: "123456" });

    for (const denied of contract.denied_strings) {
      expect(surfaced).not.toContain(denied);
    }
  });
});
