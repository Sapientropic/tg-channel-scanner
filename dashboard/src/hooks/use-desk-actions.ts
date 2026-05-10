import { useEffect, useState } from "react";

import { errorMessage, loadDeskActions, runDeskAction as runDeskActionRequest } from "../api/client";
import type { DeskAction, DeskActionResult } from "../domain/types";

export function useDeskActions() {
  const [actions, setActions] = useState<DeskAction[]>([]);
  const [results, setResults] = useState<Record<string, DeskActionResult>>({});
  const [busyActionId, setBusyActionId] = useState("");
  const [loadError, setLoadError] = useState("");
  const [runError, setRunError] = useState("");

  async function load(signal?: AbortSignal) {
    const nextActions = await loadDeskActions(signal);
    setActions(nextActions);
    setLoadError("");
  }

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal).catch((error) => {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      setLoadError(errorMessage(error));
      setActions([]);
    });
    return () => controller.abort();
  }, []);

  async function runAction(actionId: string, body: Record<string, unknown> = {}) {
    setBusyActionId(actionId);
    setRunError("");
    try {
      const result = await runDeskActionRequest(actionId, body);
      setResults((current) => ({ ...current, [actionId]: result }));
      return result;
    } catch (error) {
      setRunError(errorMessage(error));
      throw error;
    } finally {
      setBusyActionId("");
    }
  }

  return {
    actions,
    results,
    busyActionId,
    loadError,
    runError,
    refreshActions: () => load(),
    runAction,
  };
}
