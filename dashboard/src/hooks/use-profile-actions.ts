import { useState, type Dispatch, type SetStateAction } from "react";

import {
  applyProfilePatch,
  createProfileDraftNote as createProfileDraftNoteRequest,
  createProfileFromBrief as createProfileFromBriefRequest,
  createProfileMatchingPreferencesDraft as createProfileMatchingPreferencesDraftRequest,
  deleteProfile as deleteProfileRequest,
  errorMessage,
  loadProfileTemplates as loadProfileTemplatesRequest,
  previewProfileCoach as previewProfileCoachRequest,
  previewProfileFromBrief as previewProfileFromBriefRequest,
  replayProfilePatch,
  revertProfilePatch,
  setProfileAlertMode,
  setProfileEnabled as setProfileEnabledRequest,
  setProfileRuntimeSettings as setProfileRuntimeSettingsRequest,
} from "../api/client";
import type { ProfileCoachPreview, ProfileCreatePreview, ProfileCreateResult, ProfileRuntimeSettings, ProfileTemplateCatalog, Tab } from "../domain/types";

type Notice = { tone: "success" | "error"; text: string };

type UseProfileActionsOptions = {
  refresh: () => Promise<void>;
  setActiveTab: Dispatch<SetStateAction<Tab>>;
  setBusy: Dispatch<SetStateAction<boolean>>;
  setNotice: Dispatch<SetStateAction<Notice | null>>;
};

export function useProfileActions({ refresh, setActiveTab, setBusy, setNotice }: UseProfileActionsOptions) {
  const [profileCreateResult, setProfileCreateResult] = useState<ProfileCreateResult | null>(null);
  const [profileTemplates, setProfileTemplates] = useState<ProfileTemplateCatalog | null>(null);
  const [profileCreatePreview, setProfileCreatePreview] = useState<ProfileCreatePreview | null>(null);
  const [profileCoachPreview, setProfileCoachPreview] = useState<ProfileCoachPreview | null>(null);

  async function applyPatch(patchId: string) {
    setBusy(true);
    setNotice(null);
    try {
      await applyProfilePatch(patchId);
      await refresh();
      setNotice({ tone: "success", text: "Profile change applied" });
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
      setNotice({ tone: "success", text: "Profile change reverted" });
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
      setNotice({ tone: "success", text: "Profile change drafted again" });
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
    template_id?: string;
    answers?: Record<string, string>;
    preview?: ProfileCreatePreview;
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

  async function loadProfileTemplates() {
    try {
      const result = await loadProfileTemplatesRequest();
      setProfileTemplates(result);
      return result;
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
      throw error;
    }
  }

  async function previewProfileFromBrief(payload: {
    brief: string;
    template_id?: string;
    answers?: Record<string, string>;
    source_filename?: string;
    source_text?: string;
    source_base64?: string;
    confirm_external_ai?: boolean;
  }) {
    setBusy(true);
    setNotice(null);
    try {
      const result = await previewProfileFromBriefRequest(payload);
      setProfileCreatePreview(result);
      return result;
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function previewProfileCoach(profileId: string) {
    setBusy(true);
    setNotice(null);
    try {
      const result = await previewProfileCoachRequest(profileId, true);
      setProfileCoachPreview(result);
      return result;
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function deleteProfile(profileId: string) {
    setBusy(true);
    setNotice(null);
    try {
      await deleteProfileRequest(profileId);
      await refresh();
      setNotice({ tone: "success", text: "Profile deleted" });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  return {
    profileCreateResult,
    profileTemplates,
    profileCreatePreview,
    profileCoachPreview,
    applyPatch,
    revertPatch,
    replayPatch,
    setAlertMode,
    setProfileEnabled,
    setProfileRuntimeSettings,
    createProfileDraftNote,
    createProfileMatchingPreferencesDraft,
    createProfileFromBrief,
    loadProfileTemplates,
    previewProfileFromBrief,
    previewProfileCoach,
    deleteProfile,
  };
}
