import { useEffect, useState } from "react";

import {
  cancelDeskTelegramLogin,
  errorMessage,
  loadDeskTelegramStatus,
  saveDeskTelegramCredentials,
  sendDeskTelegramCode,
  verifyDeskTelegramCode,
} from "../api/client";
import type { DeskTelegramStatus } from "../domain/types";

type TelegramAction = "load" | "credentials" | "send-code" | "verify-code" | "cancel" | "";

export function useDeskTelegram() {
  const [status, setStatus] = useState<DeskTelegramStatus | null>(null);
  const [busy, setBusy] = useState<TelegramAction>("");
  const [error, setError] = useState("");

  async function load(signal?: AbortSignal) {
    setBusy("load");
    try {
      const next = await loadDeskTelegramStatus(signal);
      setStatus(next);
      setError("");
      return next;
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === "AbortError") {
        throw caught;
      }
      setError(errorMessage(caught));
      setStatus(null);
      throw caught;
    } finally {
      setBusy("");
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal).catch((caught) => {
      if (caught instanceof DOMException && caught.name === "AbortError") {
        return;
      }
    });
    return () => controller.abort();
  }, []);

  async function run(action: TelegramAction, request: () => Promise<DeskTelegramStatus>) {
    setBusy(action);
    setError("");
    try {
      const next = await request();
      setStatus(next);
      return next;
    } catch (caught) {
      setError(errorMessage(caught));
      throw caught;
    } finally {
      setBusy("");
    }
  }

  return {
    status,
    busy,
    error,
    refreshTelegram: () => load(),
    saveCredentials: (apiId: string, apiHash: string) =>
      run("credentials", () => saveDeskTelegramCredentials(apiId, apiHash)),
    sendCode: (phone: string) => run("send-code", () => sendDeskTelegramCode(phone)),
    verifyCode: (code: string, password = "") => run("verify-code", () => verifyDeskTelegramCode(code, password)),
    cancelLogin: () => run("cancel", () => cancelDeskTelegramLogin()),
  };
}
