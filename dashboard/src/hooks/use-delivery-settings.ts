import { useEffect, useState, type Dispatch, type SetStateAction } from "react";

import {
  applyDeskBotIdentity,
  clearDeskNotificationToken as clearDeskNotificationTokenRequest,
  detectDeskDeliveryChatId,
  errorMessage,
  installDeskMiniAppMenu as installDeskMiniAppMenuRequest,
  loadDeskBotGatewayStatus,
  loadDeskNotificationTokenStatus,
  saveDeskDeliveryTarget,
  saveDeskNotificationToken as saveDeskNotificationTokenRequest,
  testDeskDeliveryTarget,
} from "../api/client";
import type {
  DeliveryChatDetectionResult,
  DeliveryTestResult,
  DeskActionResult,
  DeskBotGatewayStatus,
  DeskBotIdentityResult,
  DeskMiniAppMenuResult,
  DeskNotificationTokenStatus,
} from "../domain/types";

type Notice = { tone: "success" | "error"; text: string };

type UseDeliverySettingsOptions = {
  refresh: () => Promise<void>;
  runAction: (actionId: string, body?: Record<string, unknown>) => Promise<DeskActionResult>;
  setBusy: Dispatch<SetStateAction<boolean>>;
  setNotice: Dispatch<SetStateAction<Notice | null>>;
};

export function useDeliverySettings({ refresh, runAction, setBusy, setNotice }: UseDeliverySettingsOptions) {
  const [deliveryTest, setDeliveryTest] = useState<DeliveryTestResult | null>(null);
  const [deliveryChatDetection, setDeliveryChatDetection] = useState<DeliveryChatDetectionResult | null>(null);
  const [notificationTokenStatus, setNotificationTokenStatus] = useState<DeskNotificationTokenStatus | null>(null);
  const [notificationTokenError, setNotificationTokenError] = useState<string | null>(null);
  const [botGatewayStatus, setBotGatewayStatus] = useState<DeskBotGatewayStatus | null>(null);
  const [botGatewayError, setBotGatewayError] = useState<string | null>(null);
  const [botIdentityResult, setBotIdentityResult] = useState<DeskBotIdentityResult | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    loadDeskNotificationTokenStatus(controller.signal)
      .then((token) => {
        setNotificationTokenStatus(token);
        setNotificationTokenError(null);
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setNotificationTokenError(errorMessage(error));
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    loadDeskBotGatewayStatus(controller.signal)
      .then((status) => {
        setBotGatewayStatus(status);
        setBotGatewayError(null);
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setBotGatewayError(errorMessage(error));
        }
      });
    return () => controller.abort();
  }, []);

  async function refreshNotificationTokenStatus() {
    const token = await loadDeskNotificationTokenStatus();
    setNotificationTokenStatus(token);
    setNotificationTokenError(null);
    return token;
  }

  async function refreshBotGatewayStatus() {
    const status = await loadDeskBotGatewayStatus();
    setBotGatewayStatus(status);
    setBotGatewayError(null);
    return status;
  }

  async function refreshDeliverySettings() {
    await Promise.all([
      refreshNotificationTokenStatus().catch((error) => setNotificationTokenError(errorMessage(error))),
      refreshBotGatewayStatus().catch((error) => setBotGatewayError(errorMessage(error))),
    ]);
  }

  async function saveDeliveryTarget(targetId: string, chatId: string, enabled: boolean) {
    setBusy(true);
    setNotice(null);
    try {
      await saveDeskDeliveryTarget(targetId, chatId, enabled);
      await refresh();
      await refreshBotGatewayStatus().catch((error) => setBotGatewayError(errorMessage(error)));
      setNotice({ tone: "success", text: enabled ? "Notifications enabled" : "Notification target saved muted" });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  async function testDeliveryTarget(targetId: string, chatId: string) {
    setBusy(true);
    setNotice(null);
    try {
      const result = await testDeskDeliveryTarget(targetId, chatId);
      setDeliveryTest(result);
      setNotice({ tone: result.ok ? "success" : "error", text: result.detail || result.status });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  async function detectDeliveryChatId(targetId: string) {
    setBusy(true);
    setNotice(null);
    try {
      const result = await detectDeskDeliveryChatId(targetId);
      setDeliveryChatDetection(result);
      setNotice({ tone: result.ok ? "success" : "error", text: result.detail || result.status });
      return result;
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function saveNotificationToken(token: string) {
    setBusy(true);
    setNotice(null);
    try {
      const status = await saveDeskNotificationTokenRequest(token);
      setNotificationTokenStatus(status);
      setNotificationTokenError(null);
      await refreshBotGatewayStatus().catch((error) => setBotGatewayError(errorMessage(error)));
      setNotice({ tone: "success", text: "Notification token saved" });
    } catch (error) {
      const message = errorMessage(error);
      setNotificationTokenError(message);
      setNotice({ tone: "error", text: message });
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function clearNotificationToken() {
    setBusy(true);
    setNotice(null);
    try {
      const status = await clearDeskNotificationTokenRequest();
      setNotificationTokenStatus(status);
      setNotificationTokenError(null);
      await refreshBotGatewayStatus().catch((error) => setBotGatewayError(errorMessage(error)));
      setNotice({ tone: "success", text: "Saved notification token cleared" });
    } catch (error) {
      const message = errorMessage(error);
      setNotificationTokenError(message);
      setNotice({ tone: "error", text: message });
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function applyBotIdentity() {
    setBusy(true);
    setNotice(null);
    try {
      const result = await applyDeskBotIdentity();
      setBotIdentityResult(result);
      setBotGatewayError(null);
      await refreshBotGatewayStatus().catch((error) => setBotGatewayError(errorMessage(error)));
      setNotice({ tone: "success", text: "Bot identity applied" });
    } catch (error) {
      const message = errorMessage(error);
      setBotGatewayError(message);
      setNotice({ tone: "error", text: message });
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function installMiniAppMenu(url: string): Promise<DeskMiniAppMenuResult> {
    setBusy(true);
    setNotice(null);
    try {
      const result = await installDeskMiniAppMenuRequest(url);
      await refreshBotGatewayStatus().catch((error) => setBotGatewayError(errorMessage(error)));
      setBotGatewayError(null);
      setNotice({ tone: "success", text: "Mini App enabled in Telegram" });
      return result;
    } catch (error) {
      const message = errorMessage(error);
      setBotGatewayError(message);
      setNotice({ tone: "error", text: message });
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function setBotGatewayAutostart(enabled: boolean) {
    setBusy(true);
    setNotice(null);
    try {
      const actionId = enabled ? "bot_gateway_install_autostart" : "bot_gateway_remove_autostart";
      const result = await runAction(actionId, { confirm: true });
      await refreshBotGatewayStatus().catch((error) => setBotGatewayError(errorMessage(error)));
      setNotice({ tone: result.status === "success" ? "success" : "error", text: result.title });
      if (result.status !== "success") {
        setBotGatewayError(result.detail || result.next_action || result.title);
      } else {
        setBotGatewayError(null);
      }
    } catch (error) {
      const message = errorMessage(error);
      setBotGatewayError(message);
      setNotice({ tone: "error", text: message });
      throw error;
    } finally {
      setBusy(false);
    }
  }

  return {
    deliveryTest,
    deliveryChatDetection,
    notificationTokenStatus,
    notificationTokenError,
    botGatewayStatus,
    botGatewayError,
    botIdentityResult,
    refreshDeliverySettings,
    saveDeliveryTarget,
    testDeliveryTarget,
    detectDeliveryChatId,
    saveNotificationToken,
    clearNotificationToken,
    applyBotIdentity,
    installMiniAppMenu,
    setBotGatewayAutostart,
  };
}
