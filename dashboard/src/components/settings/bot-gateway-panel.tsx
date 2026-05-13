import { CirclePause, CirclePlay, RadioTower, ShieldCheck } from "lucide-react";

import type { DeskBotGatewayStatus, DeskBotIdentityResult } from "../../domain/types";

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
  const backendLabel = botGatewayBackendLabel(status.background?.backend);
  if (status.background?.installed) {
    return `Background on · ${backendLabel}`;
  }
  if (status.background?.available) {
    return `Background off · ${backendLabel}`;
  }
  return `Background unavailable · ${backendLabel}`;
}

export function botIdentityResultLine(result: DeskBotIdentityResult | null) {
  if (!result) {
    return "";
  }
  return `${result.name} identity applied · ${result.profile_photo_updated ? "photo updated" : "photo pending"}`;
}

export function BotGatewayPanel({
  status,
  error,
  identityResult,
  busy,
  applyBotIdentity,
  installBotGatewayAutostart,
  removeBotGatewayAutostart,
}: {
  status: DeskBotGatewayStatus | null;
  error: string | null;
  identityResult: DeskBotIdentityResult | null;
  busy: boolean;
  applyBotIdentity: () => Promise<void>;
  installBotGatewayAutostart: () => Promise<void>;
  removeBotGatewayAutostart: () => Promise<void>;
}) {
  const gatewayTone = status?.gateway_status === "running" ? "enabled" : status?.gateway_status === "stale" ? "pending" : "disabled";
  const canApplyIdentity = status?.token_configured === true;
  const canInstallBackground = status?.background?.can_install === true && !status.background.installed;
  const canRemoveBackground = status?.background?.can_remove === true;
  const identityLine = botIdentityResultLine(identityResult);
  return (
    <section className="bot-gateway-panel" aria-label="Bot Gateway status">
      <div className="notification-token-head">
        <RadioTower size={16} />
        <div>
          <strong>Bot Gateway</strong>
          <small>{botGatewayStatusLine(status)}</small>
        </div>
        <span className={`status ${gatewayTone}`}>{status?.gateway_status === "running" ? "Live" : "Local"}</span>
      </div>
      <div className="bot-gateway-readout" aria-label="Bot Gateway readiness">
        <span>
          <strong>{status?.commands_installed ? "Installed" : "Menu"}</strong>
          <small>commands</small>
        </span>
        <span>
          <strong>{status?.supported_commands?.join(" ") || "/status /latest /scan"}</strong>
          <small>supported</small>
        </span>
        <span>
          <strong>{status?.start_command || "./tgcs bot run"}</strong>
          <small>start</small>
        </span>
        <span>
          <strong>{botGatewayBackgroundLine(status)}</strong>
          <small>background</small>
        </span>
      </div>
      <div className="bot-gateway-actions">
        <button
          className="text-button"
          disabled={busy || !canInstallBackground}
          onClick={() => void installBotGatewayAutostart()}
          type="button"
        >
          <CirclePlay size={15} />
          <span>{busy ? "Working" : "Turn on background"}</span>
        </button>
        <button
          className="text-button secondary"
          disabled={busy || !canRemoveBackground}
          onClick={() => void removeBotGatewayAutostart()}
          type="button"
        >
          <CirclePause size={15} />
          <span>{busy ? "Working" : "Turn off background"}</span>
        </button>
        <button
          className="text-button secondary"
          disabled={busy || !canApplyIdentity}
          onClick={() => void applyBotIdentity()}
          type="button"
        >
          <ShieldCheck size={15} />
          <span>{busy ? "Applying" : "Apply identity"}</span>
        </button>
        <span>{identityLine || "Name, descriptions, commands; photo pending JPG validation."}</span>
      </div>
      <p className={error ? "delivery-token-warning" : "delivery-note"} role={error ? "alert" : undefined}>
        {error || status?.background?.detail || status?.local_first_note || "Bot replies only while the local gateway is running."}
      </p>
    </section>
  );
}
