import { useState } from "react";
import { CheckCircle2, CirclePause, CirclePlay, ExternalLink, Globe2, RadioTower, ShieldCheck, Smartphone, Wrench } from "lucide-react";

import type { DeskBotGatewayStatus, DeskBotIdentityResult, DeskMiniAppMenuResult } from "../../domain/types";

const SETTINGS_MINIAPP_URL_STORAGE_KEY = "tgcs.settings.miniapp.publicUrl";

type SettingsMiniAppUrlState = {
  state: "needs-token" | "empty" | "invalid" | "local" | "ready" | "enabled";
  label: string;
  detail: string;
  canSubmit: boolean;
};

function initialSettingsMiniAppUrl() {
  if (typeof window === "undefined") {
    return "";
  }
  try {
    return window.localStorage.getItem(SETTINGS_MINIAPP_URL_STORAGE_KEY) || "";
  } catch {
    return "";
  }
}

function persistSettingsMiniAppUrl(url: string) {
  if (typeof window === "undefined") {
    return;
  }
  try {
    window.localStorage.setItem(SETTINGS_MINIAPP_URL_STORAGE_KEY, url);
  } catch {
    // The URL is convenience state only; losing it should not block setup.
  }
}

export function settingsMiniAppUrlState(
  status: DeskBotGatewayStatus | null,
  rawUrl: string,
  result: DeskMiniAppMenuResult | null = null,
): SettingsMiniAppUrlState {
  const tokenReady = status?.token_configured === true;
  if (!tokenReady) {
    return {
      state: "needs-token",
      label: "Needs token",
      detail: "Save the Telegram bot token first.",
      canSubmit: false,
    };
  }
  const url = rawUrl.trim();
  if (!url) {
    return {
      state: "empty",
      label: "Paste link",
      detail: "Paste a public https://.../miniapp link to add the Review button in Telegram.",
      canSubmit: false,
    };
  }
  if (result?.menu_button_updated && result.url === url) {
    return {
      state: "enabled",
      label: "Enabled",
      detail: "Telegram menu now opens Review.",
      canSubmit: false,
    };
  }
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return {
      state: "invalid",
      label: "Check link",
      detail: "Use the full public Mini App link, starting with https://.",
      canSubmit: false,
    };
  }
  if (parsed.protocol !== "https:") {
    return {
      state: "invalid",
      label: "Use HTTPS",
      detail: "Telegram requires a public HTTPS link for Mini Apps.",
      canSubmit: false,
    };
  }
  if (isLocalMiniAppHost(parsed.hostname)) {
    return {
      state: "local",
      label: "Public link needed",
      detail: "Preview works locally, but Telegram needs a public https://.../miniapp link.",
      canSubmit: false,
    };
  }
  return {
    state: "ready",
    label: "Ready",
    detail: "This will add a Review button to the saved Telegram bot menu.",
    canSubmit: true,
  };
}

function isLocalMiniAppHost(hostname: string) {
  const host = hostname.toLowerCase().replace(/^\[|\]$/g, "");
  if (host === "localhost" || host.endsWith(".localhost") || host === "::1") {
    return true;
  }
  if (host.startsWith("127.") || host.startsWith("10.") || host.startsWith("192.168.")) {
    return true;
  }
  const parts = host.split(".").map((part) => Number(part));
  if (parts.length === 4 && parts.every((part) => Number.isInteger(part))) {
    if (parts[0] === 172 && parts[1] >= 16 && parts[1] <= 31) {
      return true;
    }
    if (parts[0] === 169 && parts[1] === 254) {
      return true;
    }
  }
  return host.startsWith("fc") || host.startsWith("fd") || host.startsWith("fe80:");
}

function miniAppInstallButtonLabel(state: SettingsMiniAppUrlState, busy: boolean) {
  if (busy) {
    return "Enabling";
  }
  if (state.state === "enabled") {
    return "Enabled";
  }
  if (state.state === "needs-token") {
    return "Save token first";
  }
  if (state.state === "invalid" || state.state === "local") {
    return "Fix public link";
  }
  if (state.canSubmit) {
    return "Enable Mini App";
  }
  return "Add public link";
}

export function botGatewayStatusLine(status: DeskBotGatewayStatus | null) {
  if (!status) {
    return "Checking · token unknown · chats unknown";
  }
  const gatewayLabel = status.gateway_status === "running"
    ? "Running"
    : status.gateway_status === "stale"
      ? "Stale"
      : "Not detected";
  const tokenLabel = status.token_configured ? "token ready" : "token missing";
  const chatLabel = status.authorized_chat_count === 0
    ? "no chats"
    : `${status.authorized_chat_count} chat${status.authorized_chat_count === 1 ? "" : "s"}`;
  return `${gatewayLabel} · ${tokenLabel} · ${chatLabel}`;
}

function botGatewayBackendLabel(backend?: string) {
  if (backend === "windows_schtasks") {
    return "Windows Task Scheduler";
  }
  if (backend === "macos_launchd") {
    return "launchd";
  }
  if (backend === "linux_systemd_user") {
    return "systemd user";
  }
  return "local scheduler";
}

export function botGatewayBackgroundLine(status: DeskBotGatewayStatus | null) {
  if (!status) {
    return "Background mode unknown";
  }
  if (!status.token_configured) {
    return "Save token before background mode";
  }
  if (status.authorized_chat_count <= 0) {
    return "Add chat before background mode";
  }
  const backendLabel = botGatewayBackendLabel(status.background?.backend);
  if (status.background?.installed) {
    return `Background on · ${backendLabel}`;
  }
  if (status.background?.available) {
    return `Background off · ${backendLabel}`;
  }
  return `Background unavailable · ${backendLabel}`;
}

export function botGatewayLivenessLine(status: DeskBotGatewayStatus | null) {
  if (!status) {
    return "Bot status unknown";
  }
  if (!status.token_configured) {
    return "Bot needs a token";
  }
  if (status.authorized_chat_count <= 0) {
    return "Bot needs a chat";
  }
  if (status.gateway_status === "running") {
    return "Bot is running";
  }
  if (status.gateway_status === "stale") {
    return "Bot may be stopped";
  }
  return "Bot is stopped";
}

export function botGatewayRepairLabel(status: DeskBotGatewayStatus | null) {
  if (!status || status.gateway_status === "stale" || status.background?.installed) {
    return "Repair alerts";
  }
  return "Run in background";
}

export function botIdentityResultLine(result: DeskBotIdentityResult | null) {
  if (!result) {
    return "";
  }
  return `${result.name} identity applied · ${result.profile_photo_updated ? "photo updated" : "photo pending"}`;
}

function botGatewayUserLine(status: DeskBotGatewayStatus | null) {
  if (!status) {
    return "Checking the local bot connection.";
  }
  if (!status.token_configured) {
    return "Save a bot token before Signal Desk can send Telegram alerts.";
  }
  if (status.authorized_chat_count === 0) {
    return "Token is saved. Add a chat ID below before live alerts can send.";
  }
  if (status.gateway_status === "running") {
    return "Ready for local Telegram alerts while Signal Desk is running.";
  }
  if (status.background?.installed) {
    return "Background mode is on; Telegram alerts can keep working after login.";
  }
  if (status.gateway_status === "stale") {
    return "Bot was seen before. Turn on background mode or reopen Signal Desk to resume replies.";
  }
  return "Token and chat are saved. Turn on background mode if you want replies without keeping this window open.";
}

function botGatewayChatLabel(status: DeskBotGatewayStatus | null) {
  if (!status) {
    return "Checking";
  }
  if (status.authorized_chat_count <= 0) {
    return "Needs chat";
  }
  return `${status.authorized_chat_count} chat${status.authorized_chat_count === 1 ? "" : "s"}`;
}

function botGatewayBackgroundUserLabel(status: DeskBotGatewayStatus | null) {
  if (!status) {
    return "Checking";
  }
  if (!status.token_configured) {
    return "Needs token";
  }
  if (status.authorized_chat_count <= 0) {
    return "Needs chat";
  }
  if (status.background?.installed) {
    return "On";
  }
  if (status.background?.available) {
    return "Off";
  }
  return "Manual";
}

export function botGatewayCanInstallBackground(status: DeskBotGatewayStatus | null) {
  return Boolean(
    status?.token_configured === true &&
    status.authorized_chat_count > 0 &&
    status.background?.can_install === true &&
    !status.background.installed,
  );
}

function botGatewayCanRepair(status: DeskBotGatewayStatus | null) {
  return Boolean(
    status?.token_configured === true &&
      status.authorized_chat_count > 0 &&
      status.background?.can_install === true &&
      (status.background.installed || status.gateway_status === "stale"),
  );
}

type BotGatewayPrimaryAction = {
  kind: "install" | "repair";
  label: string;
  detail: string;
};

function botGatewayPrimaryAction(status: DeskBotGatewayStatus | null): BotGatewayPrimaryAction | null {
  if (status?.token_configured !== true || status.authorized_chat_count <= 0) {
    return null;
  }
  if (status.gateway_status === "stale" && botGatewayCanRepair(status)) {
    return {
      kind: "repair",
      label: "Repair alerts",
      detail: "Restart the local bot link so Telegram buttons and replies work again.",
    };
  }
  if (botGatewayCanInstallBackground(status)) {
    return {
      kind: "install",
      label: "Keep alerts running",
      detail: "Turn on background mode so Telegram replies can work after login.",
    };
  }
  return null;
}

function botGatewayPrimaryCopy(status: DeskBotGatewayStatus | null) {
  if (!status) {
    return {
      title: "Checking alert connection",
      detail: "Signal Desk is reading the saved bot setup.",
    };
  }
  if (!status.token_configured) {
    return {
      title: "Add a bot token first",
      detail: "Paste the BotFather token here, then add the Telegram chat below.",
    };
  }
  if (status.authorized_chat_count <= 0) {
    return {
      title: "Add your Telegram chat",
      detail: "Send /start to the bot, then detect or paste the chat ID below.",
    };
  }
  if (status.gateway_status === "stale") {
    return {
      title: "Alerts need a quick repair",
      detail: "The saved bot setup is present, but the local reply link looks stopped.",
    };
  }
  if (status.gateway_status === "running" || status.background?.installed) {
    return {
      title: "Alerts are ready",
      detail: "Telegram alerts can send to the saved chat.",
    };
  }
  if (status.background?.available) {
    return {
      title: "Make alerts persistent",
      detail: "Telegram alerts work while Signal Desk is open. Background mode keeps them available after login.",
    };
  }
  return {
    title: "Alerts are ready while this window is open",
    detail: "Background mode is unavailable here, but saved Telegram alerts can still send locally.",
  };
}

export function BotGatewayPanel({
  status,
  error,
  identityResult,
  busy,
  applyBotIdentity,
  installMiniAppMenu,
  installBotGatewayAutostart,
  removeBotGatewayAutostart,
}: {
  status: DeskBotGatewayStatus | null;
  error: string | null;
  identityResult: DeskBotIdentityResult | null;
  busy: boolean;
  applyBotIdentity: () => Promise<void>;
  installMiniAppMenu: (url: string) => Promise<DeskMiniAppMenuResult>;
  installBotGatewayAutostart: () => Promise<void>;
  removeBotGatewayAutostart: () => Promise<void>;
}) {
  const [miniAppUrl, setMiniAppUrl] = useState(initialSettingsMiniAppUrl);
  const [miniAppMenuResult, setMiniAppMenuResult] = useState<DeskMiniAppMenuResult | null>(null);
  const gatewayTone = status?.gateway_status === "running" ? "enabled" : status?.gateway_status === "stale" ? "pending" : "disabled";
  const canApplyIdentity = status?.token_configured === true;
  const canInstallBackground = botGatewayCanInstallBackground(status);
  const canRepair = botGatewayCanRepair(status);
  const canRemoveBackground = status?.background?.can_remove === true;
  const identityLine = botIdentityResultLine(identityResult);
  const repairLabel = botGatewayRepairLabel(status);
  const primaryAction = botGatewayPrimaryAction(status);
  const primaryCopy = botGatewayPrimaryCopy(status);
  const PrimaryActionIcon = primaryAction?.kind === "repair" ? Wrench : CirclePlay;
  const tokenReady = status?.token_configured === true;
  const cleanMiniAppUrl = miniAppUrl.trim();
  const miniAppUrlState = settingsMiniAppUrlState(status, miniAppUrl, miniAppMenuResult);
  const miniAppEnabled = miniAppUrlState.state === "enabled";
  const canEnableMiniApp = miniAppUrlState.canSubmit;
  return (
    <section className="bot-gateway-panel" aria-label="Bot Gateway status">
      <div className="notification-token-head">
        <RadioTower size={16} />
        <div>
          <strong>Telegram bot alerts</strong>
          <small>{botGatewayUserLine(status)}</small>
        </div>
        <span className={`status ${gatewayTone}`}>{status?.gateway_status === "running" ? "Live" : "Local"}</span>
      </div>
      <div className="bot-gateway-readout" aria-label="Bot Gateway readiness">
        <span className={`bot-gateway-health ${gatewayTone}`}>
          <strong>{botGatewayLivenessLine(status)}</strong>
          <small>{status?.safe_next_action || "Save bot setup, then repair from here if alerts stop."}</small>
        </span>
        <span>
          <strong>{status?.token_configured ? "Ready" : "Needed"}</strong>
          <small>bot token</small>
        </span>
        <span>
          <strong>{botGatewayChatLabel(status)}</strong>
          <small>alert chat</small>
        </span>
        <span>
          <strong>{botGatewayBackgroundUserLabel(status)}</strong>
          <small>background</small>
        </span>
        <span>
          <strong>{status?.commands_installed ? "Ready" : "Update"}</strong>
          <small>bot menu</small>
        </span>
      </div>
      <div className="bot-gateway-primary-action">
        <div>
          <strong>{primaryCopy.title}</strong>
          <small>{primaryAction?.detail || primaryCopy.detail}</small>
        </div>
        {primaryAction && (
          <button
            className="text-button"
            disabled={busy}
            onClick={() => void installBotGatewayAutostart()}
            type="button"
          >
            <PrimaryActionIcon size={15} />
            <span>{busy ? "Working" : primaryAction.label}</span>
          </button>
        )}
      </div>
      <form
        className="bot-gateway-miniapp"
        onSubmit={(event) => {
          event.preventDefault();
          if (!canEnableMiniApp) {
            return;
          }
          void installMiniAppMenu(cleanMiniAppUrl).then((result) => {
            persistSettingsMiniAppUrl(result.url);
            setMiniAppUrl(result.url);
            setMiniAppMenuResult(result);
          }).catch(() => undefined);
        }}
      >
        <div className="bot-gateway-miniapp-device" aria-hidden="true">
          <Smartphone size={18} />
        </div>
        <div className="bot-gateway-miniapp-copy">
          <span>Telegram Mini App</span>
          <strong>Review in Telegram</strong>
          <div className="bot-gateway-miniapp-badges" aria-label="Mini App readiness">
            <span data-state="ready">
              <CheckCircle2 size={13} />
              Ready
            </span>
            <span data-state={tokenReady ? "ready" : "needed"}>
              <ShieldCheck size={13} />
              Token
            </span>
            <span data-state="setup">
              <Globe2 size={13} />
              {miniAppUrlState.state === "ready" || miniAppUrlState.state === "enabled" ? "HTTPS" : miniAppUrlState.label}
            </span>
            <span data-state={miniAppEnabled ? "ready" : "setup"}>
              <RadioTower size={13} />
              Menu
            </span>
          </div>
        </div>
        <div className="bot-gateway-miniapp-actions" aria-label="Mini App actions">
          <a className="text-button secondary" href="/miniapp" rel="noreferrer" target="_blank">
            <ExternalLink size={15} />
            <span>Preview</span>
          </a>
        </div>
        <div className="bot-gateway-miniapp-install">
          <label className="delivery-field">
            <span>Public Mini App URL</span>
            <input
              disabled={busy || !tokenReady}
              onChange={(event) => setMiniAppUrl(event.target.value)}
              placeholder="https://your-domain.example/miniapp"
              type="url"
              value={miniAppUrl}
            />
          </label>
          <button className="text-button" disabled={busy || !canEnableMiniApp} type="submit">
            <RadioTower size={15} />
            <span>{miniAppInstallButtonLabel(miniAppUrlState, busy)}</span>
          </button>
          <small aria-live="polite">{miniAppUrlState.detail}</small>
        </div>
      </form>
      <details className="bot-gateway-technical">
        <summary>Technical details</summary>
        <div className="bot-gateway-technical-grid">
          <span>
            <strong>{botGatewayStatusLine(status)}</strong>
            <small>local status</small>
          </span>
          <span>
            <strong>{status?.supported_commands?.join(" ") || "/status /latest /scan"}</strong>
            <small>commands</small>
          </span>
          <span>
            <strong>{status?.start_command || "./tgcs bot run"}</strong>
            <small>manual start</small>
          </span>
          <span>
            <strong>{botGatewayBackgroundLine(status)}</strong>
            <small>scheduler</small>
          </span>
        </div>
        <div className="bot-gateway-technical-actions" aria-label="Bot maintenance actions">
          <button
            className="text-button secondary"
            disabled={busy || !canRepair}
            onClick={() => void installBotGatewayAutostart()}
            type="button"
          >
            <Wrench size={15} />
            <span>{busy ? "Working" : repairLabel}</span>
          </button>
          <button
            className="text-button secondary"
            disabled={busy || !canInstallBackground}
            onClick={() => void installBotGatewayAutostart()}
            type="button"
          >
            <CirclePlay size={15} />
            <span>{busy ? "Working" : "Run in background"}</span>
          </button>
          <button
            className="text-button secondary"
            disabled={busy || !canRemoveBackground}
            onClick={() => void removeBotGatewayAutostart()}
            type="button"
          >
            <CirclePause size={15} />
            <span>{busy ? "Working" : "Stop background"}</span>
          </button>
          <button
            className="text-button secondary"
            disabled={busy || !canApplyIdentity}
            onClick={() => void applyBotIdentity()}
            type="button"
          >
            <ShieldCheck size={15} />
            <span>{busy ? "Applying" : "Update bot menu"}</span>
          </button>
          <span>{identityLine || "Updates the bot name, menu, and description when a token is saved."}</span>
        </div>
      </details>
      <p className={error ? "delivery-token-warning" : "delivery-note"} role={error ? "alert" : undefined}>
        {error || status?.background?.detail || status?.local_first_note || "Bot replies only while the local gateway is running."}
      </p>
    </section>
  );
}
