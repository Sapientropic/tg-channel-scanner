import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import { ProfilesView, runtimeSettingsSaveState } from "./profiles";
import type { Profile, ProfilePatch } from "../domain/types";

function profile(overrides: Partial<Profile>): Profile {
  return {
    profile_id: "jobs-fast",
    display_name: "Jobs Fast",
    display_path: "Profiles/jobs.md",
    enabled: true,
    alert_schedule_mode: "work_hours",
    source_topics: ["jobs"],
    scan_window_hours: 2,
    semantic_max_messages: 20,
    delivery_target_count: 1,
    updated_at: "2026-05-10T00:00:00Z",
    ...overrides,
  };
}

const createProfileFromBrief = vi.fn(async () => ({
  schema_version: "desk_profile_create_result_v1" as const,
  profile_id: "new-profile",
  display_name: "New Profile",
  profile_path: "profiles/desk/new-profile.md",
  created: true,
  detail: "Profile created.",
  next_action: "Review the new profile.",
}));

describe("ProfilesView", () => {
  it("renders monitoring controls as human actions", () => {
    const html = renderToStaticMarkup(
      <ProfilesView
        profiles={[profile({ enabled: true }), profile({ profile_id: "market-news", display_name: "Market News", enabled: false })]}
        patches={[]}
        applyPatch={vi.fn()}
        revertPatch={vi.fn()}
        replayPatch={vi.fn()}
        setAlertMode={vi.fn()}
        setProfileEnabled={vi.fn()}
        setProfileRuntimeSettings={vi.fn()}
        createProfileDraftNote={vi.fn()}
        createProfileMatchingPreferencesDraft={vi.fn()}
        createProfileFromBrief={createProfileFromBrief}
        profileCreateResult={null}
        busy={false}
      />,
    );

    expect(html).toContain("Pause");
    expect(html).toContain("Resume");
    expect(html).toContain("Jobs Fast: Pause monitoring");
    expect(html).toContain("Market News: Resume monitoring");
    expect(html).toContain("Monitoring");
    expect(html).toContain("Paused");
    expect(html).toContain("2h history");
    expect(html).toContain("20 messages");
    expect(html).toContain("1 notification");
    expect(html).toContain("Edit profile");
    expect(html).not.toContain("per run");
    expect(html).not.toContain("WINDOW");
    expect(html).not.toContain("ITEMS");
    expect(html).toContain("Resume monitoring to adjust alerts.");
    expect(html).toMatch(/disabled=""/);
    expect(html).not.toContain("Profiles/jobs.md");
    expect(html).not.toContain("SEMANTIC");
    expect(html).not.toContain("COPY COMMAND");
    expect(html).not.toContain("tgcs monitor run");
    expect(html).not.toContain("Profile Drafts");
    expect(html).not.toContain("No pending preference drafts");
  });

  it("keeps new profile creation visible without opening editor noise by default", () => {
    const html = renderToStaticMarkup(
      <ProfilesView
        profiles={[]}
        patches={[]}
        applyPatch={vi.fn()}
        revertPatch={vi.fn()}
        replayPatch={vi.fn()}
        setAlertMode={vi.fn()}
        setProfileEnabled={vi.fn()}
        setProfileRuntimeSettings={vi.fn()}
        createProfileDraftNote={vi.fn()}
        createProfileMatchingPreferencesDraft={vi.fn()}
        createProfileFromBrief={createProfileFromBrief}
        profileCreateResult={null}
        busy={false}
      />,
    );

    expect(html).toContain("New profile");
    expect(html).toContain("Markdown, text, or PDF");
    expect(html).toContain("No profiles yet");
  });

  it("shows preference drafts only when there is work to review", () => {
    const patch: ProfilePatch = {
      patch_id: "patch-1",
      profile_id: "jobs-fast",
      card_title: "React contract role",
      note: "Prefer remote React roles.",
      status: "pending",
      diff_text: "-old\n+new",
      created_at: "2026-05-10T00:00:00Z",
    };
    const html = renderToStaticMarkup(
      <ProfilesView
        profiles={[profile({ enabled: true })]}
        patches={[patch]}
        applyPatch={vi.fn()}
        revertPatch={vi.fn()}
        replayPatch={vi.fn()}
        setAlertMode={vi.fn()}
        setProfileEnabled={vi.fn()}
        setProfileRuntimeSettings={vi.fn()}
        createProfileDraftNote={vi.fn()}
        createProfileMatchingPreferencesDraft={vi.fn()}
        createProfileFromBrief={createProfileFromBrief}
        profileCreateResult={null}
        busy={false}
      />,
    );

    expect(html).toContain("Profile Drafts");
    expect(html).toContain("aria-expanded=\"true\"");
    expect(html).toContain("React contract role");
    expect(html).toContain("Apply to profile");
    expect(html).toContain("Adds your manual preference");
  });

  it("offers replay only for reverted profile diffs", () => {
    const patch: ProfilePatch = {
      patch_id: "patch-1",
      profile_id: "jobs-fast",
      note: "Prefer remote React roles.",
      status: "reverted",
      diff_text: "-old\n+new",
      created_at: "2026-05-10T00:00:00Z",
    };
    const html = renderToStaticMarkup(
      <ProfilesView
        profiles={[profile({ enabled: true })]}
        patches={[patch]}
        applyPatch={vi.fn()}
        revertPatch={vi.fn()}
        replayPatch={vi.fn()}
        setAlertMode={vi.fn()}
        setProfileEnabled={vi.fn()}
        setProfileRuntimeSettings={vi.fn()}
        createProfileDraftNote={vi.fn()}
        createProfileMatchingPreferencesDraft={vi.fn()}
        createProfileFromBrief={createProfileFromBrief}
        profileCreateResult={null}
        busy={false}
      />,
    );

    expect(html).toContain("Replay");
    expect(html).not.toContain("Apply to profile");
    expect(html).not.toContain("Revert");
  });

  it("validates profile scan setting edits before save", () => {
    expect(runtimeSettingsSaveState(2, 20, "2", "20")).toMatchObject({ canSave: false });
    expect(runtimeSettingsSaveState(2, 20, "5", "35")).toMatchObject({
      canSave: true,
      scan_window_hours: 5,
      semantic_max_messages: 35,
    });
    expect(runtimeSettingsSaveState(2, 20, "0", "35")).toMatchObject({ canSave: false });
    expect(runtimeSettingsSaveState(2, 20, "5", "501")).toMatchObject({ canSave: false });
    expect(runtimeSettingsSaveState(2, 20, "six", "35")).toMatchObject({ canSave: false });
  });
});
