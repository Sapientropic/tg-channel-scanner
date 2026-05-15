import { useCallback, useEffect, useState } from "react";

import { errorMessage, loadDashboardState } from "../api/client";
import { emptyDashboardState } from "../domain/sanitize";
import type { DashboardState } from "../domain/types";

export const DASHBOARD_STATE_AUTO_REFRESH_MS = 15000;
export type DashboardLoadStatus = "loading" | "ready" | "error";

type DashboardStatePollingContext = {
  busy: boolean;
  visibilityState: DocumentVisibilityState | "visible" | "hidden";
};

export function shouldPollDashboardState({ busy, visibilityState }: DashboardStatePollingContext) {
  return !busy && visibilityState === "visible";
}

export function useDashboardState({ busy = false }: { busy?: boolean } = {}) {
  const [state, setState] = useState<DashboardState>(emptyDashboardState);
  const [loadError, setLoadError] = useState("");
  const [loadStatus, setLoadStatus] = useState<DashboardLoadStatus>("loading");

  const load = useCallback(async (signal?: AbortSignal) => {
    const nextState = await loadDashboardState(signal);
    setState(nextState);
    setLoadError("");
    setLoadStatus("ready");
  }, []);

  const handleLoadError = useCallback((error: unknown, { resetState = false }: { resetState?: boolean } = {}) => {
    if (error instanceof DOMException && error.name === "AbortError") {
      return false;
    }
    setLoadError(errorMessage(error));
    if (resetState) {
      setState(emptyDashboardState);
    }
    setLoadStatus((current) => (current === "ready" && !resetState ? "ready" : "error"));
    return true;
  }, []);

  const refresh = useCallback(async () => {
    setLoadStatus((current) => (current === "ready" ? current : "loading"));
    try {
      await load();
    } catch (error) {
      if (handleLoadError(error)) {
        throw error;
      }
    }
  }, [handleLoadError, load]);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal).catch((error) => {
      handleLoadError(error, { resetState: true });
    });
    return () => controller.abort();
  }, [handleLoadError, load]);

  useEffect(() => {
    function loadQuietly() {
      const visibilityState = typeof document === "undefined" ? "visible" : document.visibilityState;
      if (!shouldPollDashboardState({ busy, visibilityState })) {
        return;
      }
      load().catch((error) => {
        handleLoadError(error);
      });
    }
    const intervalId = window.setInterval(loadQuietly, DASHBOARD_STATE_AUTO_REFRESH_MS);
    document.addEventListener("visibilitychange", loadQuietly);
    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", loadQuietly);
    };
  }, [busy, handleLoadError, load]);

  return { state, refresh, loadError, loadStatus };
}
