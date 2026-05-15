import { describe, expect, it } from "vitest";
import fixture from "../../../tests/fixtures/contracts/profile_coach_v1.json";

import { sanitizeProfileCoachPreview, sanitizeProfileCreatePreview, sanitizeProfileTemplateCatalog } from "./sanitize";

type ProfileCoachFixture = {
  frontend_input: {
    profile_template_catalog: unknown;
    profile_create_preview: unknown;
    profile_coach_preview: unknown;
  };
  denied_strings: string[];
};

describe("Profile coach contract fixtures", () => {
  it("sanitizes profile preview and coach payloads without private fields", () => {
    const contract = fixture as ProfileCoachFixture;
    const picked = {
      profile_template_catalog: sanitizeProfileTemplateCatalog(contract.frontend_input.profile_template_catalog),
      profile_create_preview: sanitizeProfileCreatePreview(contract.frontend_input.profile_create_preview),
      profile_coach_preview: sanitizeProfileCoachPreview(contract.frontend_input.profile_coach_preview),
    };
    const surfaced = JSON.stringify(picked);

    expect(picked.profile_template_catalog?.schema_version).toBe("desk_profile_template_catalog_v1");
    expect(picked.profile_create_preview?.schema_version).toBe("desk_profile_create_preview_v1");
    expect(picked.profile_coach_preview?.schema_version).toBe("profile_coach_preview_v1");
    for (const denied of contract.denied_strings) {
      expect(surfaced).not.toContain(denied);
    }
  });
});
