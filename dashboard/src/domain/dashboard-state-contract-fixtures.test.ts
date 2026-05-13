import { describe, expect, it } from "vitest";
import fixture from "../../../tests/fixtures/contracts/dashboard_state_v1.projection.json";

import { sanitizeDashboardState } from "./sanitize";

type DashboardStateContractFixture = {
  frontend_input: unknown;
  frontend_expected: {
    inbox: unknown;
    delivery_targets: unknown;
  };
  denied_strings: string[];
};

function pickFrontendContractState(value: unknown) {
  const state = sanitizeDashboardState(value);
  return {
    inbox: state.inbox.map((card) => {
      const contractCard = card as typeof card & { opportunity_status?: string };
      return {
        schema_version: card.schema_version,
        card_id: card.card_id,
        profile_id: card.profile_id,
        title: card.title,
        rating: card.rating,
        decision_status: card.decision_status,
        source_refs: card.source_refs,
        item: card.item,
        status: card.status,
        opportunity_status: contractCard.opportunity_status ?? "open",
      };
    }),
    delivery_targets: state.delivery_targets.map((target) => ({
      schema_version: target.schema_version,
      target_id: target.target_id,
      type: target.type,
      enabled: target.enabled,
      config: target.config,
    })),
  };
}

describe("dashboard_state_v1 contract fixture", () => {
  it("keeps private fields out of sanitized dashboard projections", () => {
    const contract = fixture as DashboardStateContractFixture;
    const picked = pickFrontendContractState(contract.frontend_input);
    const surfaced = JSON.stringify(picked);

    expect(picked).toEqual(contract.frontend_expected);
    for (const denied of contract.denied_strings) {
      expect(surfaced).not.toContain(denied);
    }
  });
});
