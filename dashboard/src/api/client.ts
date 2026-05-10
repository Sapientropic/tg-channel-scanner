import {
  sanitizeDashboardState,
  sanitizeDeskActions,
  sanitizeDeskActionResult,
  sanitizeDeskNotificationTokenStatus,
  sanitizeDeskSchedulerStatus,
  sanitizeDeskSourcesResult,
  sanitizeDeskTelegramStatus,
  sanitizeDeliveryTestResult,
  sanitizeFeedbackExportResult,
  sanitizeGitUpdateStatus,
  sanitizeSourceImportResult,
} from "../domain/sanitize";
import type {
  DashboardState,
  DeskAction,
  DeskActionResult,
  DeskNotificationTokenStatus,
  DeskSchedulerStatus,
  DeskSourcesResult,
  DeskTelegramStatus,
  DeliveryTarget,
  DeliveryTestResult,
  FeedbackExportResult,
  GitUpdateStatus,
  SourceImportResult,
} from "../domain/types";

export async function loadDashboardState(signal?: AbortSignal): Promise<DashboardState> {
  const response = await fetch("/api/state", { signal });
  await assertOk(response);
  return sanitizeDashboardState(await response.json());
}

export async function postReviewCardAction(cardId: string, action: string, note = "") {
  const response = await fetch(`/api/review-cards/${encodeURIComponent(cardId)}/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, note }),
  });
  await assertOk(response);
}

export async function applyProfilePatch(patchId: string) {
  const response = await fetch(`/api/profile-patches/${encodeURIComponent(patchId)}/apply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  await assertOk(response);
}

export async function revertProfilePatch(patchId: string) {
  const response = await fetch(`/api/profile-patches/${encodeURIComponent(patchId)}/revert`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  await assertOk(response);
}

export async function setProfileAlertMode(profileId: string, mode: string) {
  const response = await fetch(`/api/profiles/${encodeURIComponent(profileId)}/alert-mode`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode }),
  });
  await assertOk(response);
}

export async function setProfileEnabled(profileId: string, enabled: boolean) {
  const response = await fetch(`/api/profiles/${encodeURIComponent(profileId)}/enabled`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  await assertOk(response);
}

export async function setProfileRuntimeSettings(
  profileId: string,
  settings: { scan_window_hours?: number; semantic_max_messages?: number },
) {
  const response = await fetch(`/api/profiles/${encodeURIComponent(profileId)}/runtime-settings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
  await assertOk(response);
}

export async function checkGitUpdates(): Promise<GitUpdateStatus> {
  const payload = await postJson("/api/git/check-updates", {});
  const git = sanitizeGitUpdateStatus(payload.git);
  if (!git) {
    throw new Error("Invalid git status response");
  }
  return git;
}

export async function pullLatestGit(): Promise<GitUpdateStatus> {
  const payload = await postJson("/api/git/pull-latest", { confirm: true });
  const git = sanitizeGitUpdateStatus(payload.git);
  if (!git) {
    throw new Error("Invalid git status response");
  }
  return git;
}

export async function exportFeedback(): Promise<FeedbackExportResult> {
  const payload = await postJson("/api/feedback/export", {});
  const result = sanitizeFeedbackExportResult(payload.export);
  if (!result) {
    throw new Error("Invalid feedback export response");
  }
  return result;
}

export async function loadDeskActions(signal?: AbortSignal): Promise<DeskAction[]> {
  const response = await fetch("/api/desk/actions", { signal });
  const payload = await readJson(response);
  return sanitizeDeskActions(payload);
}

export async function loadDeskSchedulerStatus(signal?: AbortSignal): Promise<DeskSchedulerStatus> {
  const response = await fetch("/api/desk/scheduler-status", { signal });
  const payload = await readJson(response);
  const result = sanitizeDeskSchedulerStatus(payload.scheduler);
  if (!result) {
    throw new Error("Invalid scheduler status response");
  }
  return result;
}

export async function loadDeskNotificationTokenStatus(signal?: AbortSignal): Promise<DeskNotificationTokenStatus> {
  const response = await fetch("/api/desk/notification-token/status", { signal });
  const payload = await readJson(response);
  const result = sanitizeDeskNotificationTokenStatus(payload.token);
  if (!result) {
    throw new Error("Invalid notification token response");
  }
  return result;
}

export async function saveDeskNotificationToken(token: string): Promise<DeskNotificationTokenStatus> {
  const payload = await postJson("/api/desk/notification-token", { token });
  const result = sanitizeDeskNotificationTokenStatus(payload.token);
  if (!result) {
    throw new Error("Invalid notification token response");
  }
  return result;
}

export async function clearDeskNotificationToken(): Promise<DeskNotificationTokenStatus> {
  const payload = await postJson("/api/desk/notification-token", { clear: true });
  const result = sanitizeDeskNotificationTokenStatus(payload.token);
  if (!result) {
    throw new Error("Invalid notification token response");
  }
  return result;
}

export async function loadDeskSources(signal?: AbortSignal): Promise<DeskSourcesResult> {
  const response = await fetch("/api/desk/sources", { signal });
  const payload = await readJson(response);
  const result = sanitizeDeskSourcesResult(payload.sources);
  if (!result) {
    throw new Error("Invalid source library response");
  }
  return result;
}

export async function runDeskAction(
  actionId: string,
  body: Record<string, unknown> = {},
  signal?: AbortSignal,
): Promise<DeskActionResult> {
  const payload = await postJson(`/api/desk/actions/${encodeURIComponent(actionId)}/run`, body, signal);
  const result = sanitizeDeskActionResult(payload.result);
  if (!result) {
    throw new Error("Invalid Desk action response");
  }
  return result;
}

export async function loadDeskTelegramStatus(signal?: AbortSignal): Promise<DeskTelegramStatus> {
  const response = await fetch("/api/desk/telegram-status", { signal });
  const payload = await readJson(response);
  const result = sanitizeDeskTelegramStatus(payload.telegram);
  if (!result) {
    throw new Error("Invalid Telegram status response");
  }
  return result;
}

export async function saveDeskTelegramCredentials(apiId: string, apiHash: string): Promise<DeskTelegramStatus> {
  const payload = await postJson("/api/desk/telegram-credentials", { api_id: apiId, api_hash: apiHash });
  const result = sanitizeDeskTelegramStatus(payload.telegram);
  if (!result) {
    throw new Error("Invalid Telegram credentials response");
  }
  return result;
}

export async function sendDeskTelegramCode(phone: string): Promise<DeskTelegramStatus> {
  const payload = await postJson("/api/desk/telegram-login/send-code", { phone });
  const result = sanitizeDeskTelegramStatus(payload.telegram);
  if (!result) {
    throw new Error("Invalid Telegram login response");
  }
  return result;
}

export async function verifyDeskTelegramCode(code: string, password = ""): Promise<DeskTelegramStatus> {
  const payload = await postJson("/api/desk/telegram-login/verify-code", { code, password });
  const result = sanitizeDeskTelegramStatus(payload.telegram);
  if (!result) {
    throw new Error("Invalid Telegram login response");
  }
  return result;
}

export async function cancelDeskTelegramLogin(): Promise<DeskTelegramStatus> {
  const payload = await postJson("/api/desk/telegram-login/cancel", {});
  const result = sanitizeDeskTelegramStatus(payload.telegram);
  if (!result) {
    throw new Error("Invalid Telegram login response");
  }
  return result;
}

export async function saveDeskDeliveryTarget(
  targetId: string,
  chatId: string,
  enabled: boolean,
): Promise<DeliveryTarget> {
  const payload = await postJson(`/api/desk/delivery-targets/${encodeURIComponent(targetId)}`, {
    chat_id: chatId,
    enabled,
  });
  const state = sanitizeDashboardState({ delivery_targets: [payload.target] });
  const target = state.delivery_targets[0];
  if (!target) {
    throw new Error("Invalid notification target response");
  }
  return target;
}

export async function testDeskDeliveryTarget(targetId: string, chatId: string): Promise<DeliveryTestResult> {
  const payload = await postJson(`/api/desk/delivery-targets/${encodeURIComponent(targetId)}/test`, { chat_id: chatId });
  const result = sanitizeDeliveryTestResult(payload.result);
  if (!result) {
    throw new Error("Invalid notification test response");
  }
  return result;
}

export async function previewDeskSourceImport(sources: string, topic: string): Promise<SourceImportResult> {
  const payload = await postJson("/api/desk/sources/preview", { sources, topic });
  const result = sanitizeSourceImportResult(payload.result);
  if (!result) {
    throw new Error("Invalid source preview response");
  }
  return result;
}

export async function importDeskSources(sources: string, topic: string): Promise<SourceImportResult> {
  const payload = await postJson("/api/desk/sources/import", { sources, topic });
  const result = sanitizeSourceImportResult(payload.result);
  if (!result) {
    throw new Error("Invalid source import response");
  }
  return result;
}

export async function setDeskSourceEnabled(sourceId: string, enabled: boolean): Promise<DeskSourcesResult> {
  const payload = await postJson(`/api/desk/sources/${encodeURIComponent(sourceId)}/enabled`, { enabled });
  const result = sanitizeDeskSourcesResult(payload.sources);
  if (!result) {
    throw new Error("Invalid source library response");
  }
  return result;
}

export async function setDeskSourceTopics(sourceId: string, topics: string[]): Promise<DeskSourcesResult> {
  assertDeskSourceTopics(topics);
  const payload = await postJson(`/api/desk/sources/${encodeURIComponent(sourceId)}/topics`, { topics });
  const result = sanitizeDeskSourcesResult(payload.sources);
  if (!result) {
    throw new Error("Invalid source library response");
  }
  return result;
}

function assertDeskSourceTopics(topics: string[]) {
  if (!Array.isArray(topics) || topics.length < 1 || topics.length > 8) {
    throw new Error("Use 1 to 8 topic tags.");
  }
  for (const topic of topics) {
    if (typeof topic !== "string" || !/^[a-z0-9][a-z0-9_-]{1,40}$/.test(topic)) {
      throw new Error("Use short topic tags like jobs or remote-work.");
    }
  }
}

async function postJson(path: string, body: Record<string, unknown>, signal?: AbortSignal) {
  return readJson(
    await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    }),
  );
}

async function assertOk(response: Response) {
  if (response.ok) {
    return;
  }
  let detail = response.statusText;
  try {
    const payload = await response.json();
    if (payload && typeof payload.error === "string") {
      detail = payload.error;
    }
  } catch {
    // Keep the HTTP status text when the server did not return JSON.
  }
  throw new Error(detail || `HTTP ${response.status}`);
}

async function readJson(response: Response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = typeof payload.error === "string" ? payload.error : response.statusText || `HTTP ${response.status}`;
    throw new Error(message);
  }
  return payload as Record<string, unknown>;
}

export function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}
