import { useEffect, useState } from "react";

import { errorMessage, loadDashboardState } from "../api/client";
import { emptyDashboardState } from "../domain/sanitize";
import type { DashboardState } from "../domain/types";

export function useDashboardState() {
  const [state, setState] = useState<DashboardState>(emptyDashboardState);
  const [loadError, setLoadError] = useState("");

  async function load(signal?: AbortSignal) {
    const nextState = await loadDashboardState(signal);
    setState(nextState);
    setLoadError("");
  }

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal).catch((error) => {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      setLoadError(errorMessage(error));
      setState(emptyDashboardState);
    });
    return () => controller.abort();
  }, []);

  return { state, refresh: () => load(), loadError };
}
