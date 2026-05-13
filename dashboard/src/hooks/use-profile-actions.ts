import { useState, type Dispatch, type SetStateAction } from "react";

import {
  applyProfilePatch,
  createProfileDraftNote as createProfileDraftNoteRequest,
  createProfileFromBrief as createProfileFromBriefRequest,
  createProfileMatchingPreferencesDraft as createProfileMatchingPreferencesDraftRequest,
  errorMessage,
  replayProfilePatch,
  revertProfilePatch,
  setProfileAlertMode,
  setProfileEnabled as setProfileEnabledRequest,
  setProfileRuntimeSettings as setProfileRuntimeSettingsRequest,
} from "../api/client";
import type { ProfileCreateResult, ProfileRuntimeSettings, Tab } from "../domain/types";

type Notice = { tone: "success" | "error"; text: string };

type UseProfileActionsOptions = {
  refresh: () => Promise<void>;
  setActiveTab: Dispatch<SetStateAction<Tab>>;
  setBusy: Dispatch<SetStateAction<boolean>>;
  setNotice: Dispatch<SetStateAction<Notice | null>>;
};

export function useProfileActions({ refresh, setActiveTab, setBusy, setNotice }: UseProfileActionsOptions) {
  const [profileCreateResult, setProfileCreateResult] = useState<ProfileCreateResult | null>(null);

  async function applyPatch(patchId: string) {
    setBusy(true);
    setNotice(null);
    try {
      await applyProfilePatch(patchId);
      await refresh();
      setNotice({ tone: "success", text: "Profile snapshot saved and diff applied" });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  async function revertPatch(patchId: string) {
    setBusy(true);
    setNotice(null);
    try {
      await revertProfilePatch(patchId);
      await refresh();
      setNotice({ tone: "success", text: "Profile diff reverted from saved snapshot" });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  async function replayPatch(patchId: string) {
    setBusy(true);
    setNotice(null);
    try {
      await replayProfilePatch(patchId);
      await refresh();
      setNotice({ tone: "success", text: "Profile diff replayed for review" });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  async function setAlertMode(profileId: string, mode: string) {
    setBusy(true);
    setNotice(null);
    try {
      await setProfileAlertMode(profileId, mode);
      await refresh();
      setNotice({ tone: "success", text: "Alert mode updated" });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  async function setProfileEnabled(profileId: string, enabled: boolean) {
    setBusy(true);
    setNotice(null);
    try {
      await setProfileEnabledRequest(profileId, enabled);
      await refresh();
      setNotice({ tone: "success", text: enabled ? "Profile enabled" : "Profile paused" });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  async function setProfileRuntimeSettings(profileId: string, settings: ProfileRuntimeSettings) {
    setBusy(true);
    setNotice(null);
    try {
      await setProfileRuntimeSettingsRequest(profileId, settings);
      await refresh();
      setNotice({ tone: "success", text: "Profile scan settings saved" });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  async function createProfileDraftNote(profileId: string, note: string) {
    setBusy(true);
    setNotice(null);
    try {
      await createProfileDraftNoteRequest(profileId, note);
      await refresh();
      setActiveTab("profiles");
      setNotice({ tone: "success", text: "Profile draft created. Review it before applying." });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function createProfileMatchingPreferencesDraft(profileId: string, preferences: string) {
    setBusy(true);
    setNotice(null);
    try {
      await createProfileMatchingPreferencesDraftRequest(profileId, preferences);
      await refresh();
      setActiveTab("profiles");
      setNotice({ tone: "success", text: "Matching change drafted. Preview it before applying." });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function createProfileFromBrief(payload: {
    brief: string;
    source_filename?: string;
    source_text?: string;
    source_base64?: string;
  }) {
    setBusy(true);
    setNotice(null);
    try {
      const result = await createProfileFromBriefRequest(payload);
      setProfileCreateResult(result);
      await refresh();
      setActiveTab("profiles");
      setNotice({ tone: "success", text: result.detail || "Profile created" });
      return result;
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
      throw error;
    } finally {
      setBusy(false);
    }
  }

  return {
    profileCreateResult,
    applyPatch,
    revertPatch,
    replayPatch,
    setAlertMode,
    setProfileEnabled,
    setProfileRuntimeSettings,
    createProfileDraftNote,
    createProfileMatchingPreferencesDraft,
    createProfileFromBrief,
  };
}
