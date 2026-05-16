import { useEffect, useState, type Dispatch, type SetStateAction } from "react";

import {
  clearDeskAiApiKey as clearDeskAiApiKeyRequest,
  errorMessage,
  exportDeskSupportDiagnostics as exportDeskSupportDiagnosticsRequest,
  loadDeskAiSettingsStatus,
  loadDeskSchedulerStatus,
  loadDeskSupportStatus,
  revealDeskSupportTarget as revealDeskSupportTargetRequest,
  saveDeskAiApiKey as saveDeskAiApiKeyRequest,
} from "../api/client";
import type { DeskAiSettingsStatus, DeskSchedulerStatus, DeskSupportDiagnosticExportResult, DeskSupportStatus } from "../domain/types";

type Notice = { tone: "success" | "error"; text: string };

type UseStatusSurfacesOptions = {
  setBusy: Dispatch<SetStateAction<boolean>>;
  setNotice: Dispatch<SetStateAction<Notice | null>>;
};

export function useStatusSurfaces({ setBusy, setNotice }: UseStatusSurfacesOptions) {
  const [aiSettingsStatus, setAiSettingsStatus] = useState<DeskAiSettingsStatus | null>(null);
  const [aiSettingsError, setAiSettingsError] = useState<string | null>(null);
  const [deskSchedulerStatus, setDeskSchedulerStatus] = useState<DeskSchedulerStatus | null>(null);
  const [deskSchedulerError, setDeskSchedulerError] = useState<string | null>(null);
  const [deskSupportStatus, setDeskSupportStatus] = useState<DeskSupportStatus | null>(null);
  const [deskSupportError, setDeskSupportError] = useState<string | null>(null);
  const [deskSupportExportResult, setDeskSupportExportResult] = useState<DeskSupportDiagnosticExportResult | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    loadDeskSchedulerStatus(controller.signal)
      .then((scheduler) => {
        setDeskSchedulerStatus(scheduler);
        setDeskSchedulerError(null);
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setDeskSchedulerError(errorMessage(error));
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadDeskAiSettingsStatus(controller.signal)
      .then((status) => {
        setAiSettingsStatus(status);
        setAiSettingsError(null);
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setAiSettingsError(errorMessage(error));
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadDeskSupportStatus(controller.signal)
      .then((status) => {
        setDeskSupportStatus(status);
        setDeskSupportError(null);
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setDeskSupportError(errorMessage(error));
        }
      });
    return () => controller.abort();
  }, []);

  async function refreshDeskSchedulerStatus() {
    const scheduler = await loadDeskSchedulerStatus();
    setDeskSchedulerStatus(scheduler);
    setDeskSchedulerError(null);
    return scheduler;
  }

  async function refreshAiSettingsStatus() {
    const status = await loadDeskAiSettingsStatus();
    setAiSettingsStatus(status);
    setAiSettingsError(null);
    return status;
  }

  async function refreshDeskSupportStatus() {
    const status = await loadDeskSupportStatus();
    setDeskSupportStatus(status);
    setDeskSupportError(null);
    return status;
  }

  async function revealDeskSupportTarget(target: string) {
    setBusy(true);
    setNotice(null);
    try {
      await revealDeskSupportTargetRequest(target);
      setNotice({ tone: "success", text: "Opened support path in Finder" });
    } catch (error) {
      const message = errorMessage(error);
      setDeskSupportError(message);
      setNotice({ tone: "error", text: message });
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function exportDeskSupportDiagnostics() {
    setBusy(true);
    setNotice(null);
    try {
      const result = await exportDeskSupportDiagnosticsRequest();
      setDeskSupportExportResult(result);
      setDeskSupportError(null);
      setNotice({ tone: "success", text: "Support snapshot saved" });
      return result;
    } catch (error) {
      const message = errorMessage(error);
      setDeskSupportError(message);
      setNotice({ tone: "error", text: message });
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function refreshStatusSurfaces() {
    await Promise.all([
      refreshDeskSchedulerStatus().catch((error) => setDeskSchedulerError(errorMessage(error))),
      refreshAiSettingsStatus().catch((error) => setAiSettingsError(errorMessage(error))),
      refreshDeskSupportStatus().catch((error) => setDeskSupportError(errorMessage(error))),
    ]);
  }

  async function saveAiApiKey(provider: string, apiKey: string) {
    setBusy(true);
    setNotice(null);
    try {
      const status = await saveDeskAiApiKeyRequest(provider, apiKey);
      setAiSettingsStatus(status);
      setAiSettingsError(null);
      setNotice({ tone: "success", text: "AI API key saved" });
    } catch (error) {
      const message = errorMessage(error);
      setAiSettingsError(message);
      setNotice({ tone: "error", text: message });
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function clearAiApiKey(provider: string) {
    setBusy(true);
    setNotice(null);
    try {
      const status = await clearDeskAiApiKeyRequest(provider);
      setAiSettingsStatus(status);
      setAiSettingsError(null);
      setNotice({ tone: "success", text: "Saved AI API key cleared" });
    } catch (error) {
      const message = errorMessage(error);
      setAiSettingsError(message);
      setNotice({ tone: "error", text: message });
      throw error;
    } finally {
      setBusy(false);
    }
  }

  return {
    aiSettingsStatus,
    aiSettingsError,
    deskSchedulerStatus,
    deskSchedulerError,
    deskSupportStatus,
    deskSupportError,
    deskSupportExportResult,
    refreshStatusSurfaces,
    refreshDeskSchedulerStatus,
    refreshDeskSupportStatus,
    revealDeskSupportTarget,
    exportDeskSupportDiagnostics,
    saveAiApiKey,
    clearAiApiKey,
  };
}
