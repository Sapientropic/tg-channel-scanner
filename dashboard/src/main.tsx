import { StrictMode, useCallback, useEffect, useMemo, useRef, useState, type MutableRefObject, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import {
  Inbox,
  Rocket,
  Play,
  Settings,
  UserRoundCog,
} from "lucide-react";
import {
  applyProfilePatch,
  checkGitUpdates as checkGitUpdatesRequest,
  clearFeedbackDecisions as clearFeedbackDecisionsRequest,
  clearDeskNotificationToken as clearDeskNotificationTokenRequest,
  errorMessage,
  exportFeedback as exportFeedbackRequest,
  importDeskSources,
  loadDeskNotificationTokenStatus,
  loadDeskSources,
  loadDeskSchedulerStatus,
  postReviewCardAction,
  previewDeskSourceImport,
  pullLatestGit,
  revertProfilePatch,
  saveDeskDeliveryTarget,
  saveDeskNotificationToken as saveDeskNotificationTokenRequest,
  setDeskSourceEnabled as setDeskSourceEnabledRequest,
  setDeskSourceTopics as setDeskSourceTopicsRequest,
  setProfileAlertMode,
  setProfileEnabled as setProfileEnabledRequest,
  setProfileRuntimeSettings as setProfileRuntimeSettingsRequest,
  testDeskDeliveryTarget,
  undoReviewCardAction,
} from "./api/client";
import { ActionsView } from "./components/actions";
import { CommandStrip, OpportunitySummaryPanel, ValidationSummaryPanel } from "./components/board-status";
import { InboxView } from "./components/inbox";
import { ProfilesView } from "./components/profiles";
import { RunsView } from "./components/runs";
import { SettingsView } from "./components/settings";
import { ConsoleHeader, NavigationRail, WorkbenchHeader } from "./components/shell";
import { StatusRail } from "./components/status-rail";
import { buildProfileReportNames } from "./domain/display";
import { isActionableInboxCard } from "./domain/inbox";
import {
  buildBoardMeta,
  buildMetrics,
  buildTabCounts,
  hasBlockingOpportunitySummary,
} from "./domain/projections";
import { useDashboardState } from "./hooks/use-dashboard-state";
import { useDeskActions } from "./hooks/use-desk-actions";
import { useDeskTelegram } from "./hooks/use-desk-telegram";
import type {
  DeliveryTestResult,
  DeskNotificationTokenStatus,
  DeskSchedulerStatus,
  DeskSourcesResult,
  FeedbackExportResult,
  GitUpdateStatus,
  SourceImportResult,
  Tab,
} from "./domain/types";
import "./styles.css";

const tabShell: Array<{ tab: Tab; icon: ReactNode; label: string }> = [
  { tab: "inbox", icon: <Inbox size={17} />, label: "Review" },
  { tab: "actions", icon: <Rocket size={17} />, label: "Start" },
  { tab: "profiles", icon: <UserRoundCog size={17} />, label: "Profiles" },
  { tab: "runs", icon: <Play size={17} />, label: "Runs" },
  { tab: "settings", icon: <Settings size={17} />, label: "Settings" },
];
const startStepCount = 6;

type DeskActionConfirmation = {
  actionId: string;
  title: string;
  detail: string;
  confirmLabel: string;
};

function App() {
  const { state, refresh, loadError } = useDashboardState();
  const {
    actions: deskActions,
    results: deskActionResults,
    busyActionId,
    loadError: deskActionsLoadError,
    runError: deskActionRunError,
    runAction,
  } = useDeskActions();
  const deskTelegram = useDeskTelegram();
  const [activeTab, setActiveTab] = useState<Tab>("inbox");
  const [busy, setBusy] = useState(false);
  const [gitBusy, setGitBusy] = useState(false);
  const [gitStatus, setGitStatus] = useState<GitUpdateStatus | null>(null);
  const [feedbackExport, setFeedbackExport] = useState<FeedbackExportResult | null>(null);
  const [deliveryTest, setDeliveryTest] = useState<DeliveryTestResult | null>(null);
  const [notificationTokenStatus, setNotificationTokenStatus] = useState<DeskNotificationTokenStatus | null>(null);
  const [notificationTokenError, setNotificationTokenError] = useState<string | null>(null);
  const [sourceImportResult, setSourceImportResult] = useState<SourceImportResult | null>(null);
  const [deskSources, setDeskSources] = useState<DeskSourcesResult | null>(null);
  const [deskSourcesError, setDeskSourcesError] = useState<string | null>(null);
  const [deskSchedulerStatus, setDeskSchedulerStatus] = useState<DeskSchedulerStatus | null>(null);
  const [deskSchedulerError, setDeskSchedulerError] = useState<string | null>(null);
  const [pendingDeskAction, setPendingDeskAction] = useState<DeskActionConfirmation | null>(null);
  const pendingDeskActionReturnFocus = useRef<HTMLElement | null>(null);
  const [settingsFocusTarget, setSettingsFocusTarget] = useState<"notifications" | null>(null);
  const [notice, setNotice] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  const metrics = useMemo(() => buildMetrics(state), [state]);
  const profileReportNames = useMemo(() => buildProfileReportNames(state.profiles), [state.profiles]);
  const tabCounts = useMemo(() => buildTabCounts(state, startStepCount), [state]);
  const boardMeta = useMemo(() => buildBoardMeta(activeTab, state, startStepCount), [activeTab, state]);
  const latestRunId = state.runs[0]?.run_id;
  const hasLatestActionCards = state.inbox.some((card) => isActionableInboxCard(card, latestRunId));
  const hasBlockingSummary = hasBlockingOpportunitySummary(state.opportunity_summary);
  const showCommandStrip = activeTab === "inbox" && !hasLatestActionCards;
  const showOpportunitySummary = activeTab === "inbox" && (!hasLatestActionCards || hasBlockingSummary);
  const showValidationSummary = activeTab === "inbox" && !hasLatestActionCards;
  const showBoardStatusStack = showCommandStrip || showOpportunitySummary || showValidationSummary;

  useEffect(() => {
    // Mobile bottom navigation can otherwise carry the previous tab's scroll
    // offset into the next screen, hiding the new tab's main decision surface.
    window.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }, [activeTab]);

  useEffect(() => {
    const controller = new AbortController();
    loadDeskSources(controller.signal)
      .then((sources) => {
        setDeskSources(sources);
        setDeskSourcesError(null);
      })
      .catch((error) => {
        if (!controller.signal.aborted) {
          setDeskSourcesError(errorMessage(error));
        }
      });
    return () => controller.abort();
  }, []);

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

  async function refreshDeskSources() {
    const sources = await loadDeskSources();
    setDeskSources(sources);
    setDeskSourcesError(null);
    return sources;
  }

  async function refreshDeskSchedulerStatus() {
    const scheduler = await loadDeskSchedulerStatus();
    setDeskSchedulerStatus(scheduler);
    setDeskSchedulerError(null);
    return scheduler;
  }

  async function refreshNotificationTokenStatus() {
    const token = await loadDeskNotificationTokenStatus();
    setNotificationTokenStatus(token);
    setNotificationTokenError(null);
    return token;
  }

  async function refreshNow() {
    setBusy(true);
    try {
      await refresh();
      await refreshDeskSchedulerStatus().catch((error) => setDeskSchedulerError(errorMessage(error)));
      await refreshNotificationTokenStatus().catch((error) => setNotificationTokenError(errorMessage(error)));
      setNotice({ tone: "success", text: "State refreshed" });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  async function act(cardId: string, action: string, note = "") {
    setBusy(true);
    setNotice(null);
    try {
      await postReviewCardAction(cardId, action, note);
      await refresh();
      setNotice({ tone: "success", text: action === "follow_up" ? "Profile diff drafted" : "Inbox updated" });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  async function applyPatch(patchId: string) {
    setBusy(true);
    setNotice(null);
    try {
      await applyProfilePatch(patchId);
      await refresh();
      setNotice({ tone: "success", text: "Profile snapshot saved and diff applied" });
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
      setNotice({ tone: "success", text: "Profile diff reverted from saved snapshot" });
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

  async function checkUpdates() {
    setGitBusy(true);
    setNotice(null);
    try {
      const git = await checkGitUpdatesRequest();
      setGitStatus(git);
      setNotice({ tone: "success", text: "Remote status checked" });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setGitBusy(false);
    }
  }

  async function exportFeedback() {
    setBusy(true);
    setNotice(null);
    try {
      const result = await exportFeedbackRequest();
      setFeedbackExport(result);
      await refresh();
      setNotice({ tone: "success", text: `${result.feedback_count} decisions applied to future reports` });
    } catch (error) {
      setNotice({ tone: "error", text: feedbackClearErrorMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  function feedbackClearErrorMessage(error: unknown) {
    const message = errorMessage(error);
    if (/404|not found/i.test(message)) {
      return "Signal Desk server is out of date. Close and reopen Signal Desk, then retry Clear learning decisions.";
    }
    return message;
  }

  async function clearFeedback() {
    setBusy(true);
    setNotice(null);
    let successText = "";
    try {
      const clearedCount = await clearFeedbackDecisionsRequest();
      setFeedbackExport(null);
      await refresh();
      successText = clearedCount > 0 ? `${clearedCount} learning decisions cleared` : "No learning decisions to clear";
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setBusy(false);
    }
    if (successText) {
      setNotice({ tone: "success", text: successText });
    }
  }

  async function undoFeedbackDecision(cardId: string) {
    if (!cardId) {
      return;
    }
    setBusy(true);
    setNotice(null);
    try {
      await undoReviewCardAction(cardId);
      await refresh();
      setNotice({ tone: "success", text: "Decision undone" });
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

  async function setProfileRuntimeSettings(profileId: string, settings: { scan_window_hours?: number; semantic_max_messages?: number }) {
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

  async function saveDeliveryTarget(targetId: string, chatId: string, enabled: boolean) {
    setBusy(true);
    setNotice(null);
    try {
      await saveDeskDeliveryTarget(targetId, chatId, enabled);
      await refresh();
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

  async function saveNotificationToken(token: string) {
    setBusy(true);
    setNotice(null);
    try {
      const status = await saveDeskNotificationTokenRequest(token);
      setNotificationTokenStatus(status);
      setNotificationTokenError(null);
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

  async function previewSourceImport(sources: string, topic: string) {
    setBusy(true);
    setNotice(null);
    try {
      const result = await previewDeskSourceImport(sources, topic);
      setSourceImportResult(result);
      setNotice({ tone: "success", text: result.detail || result.title || "Source preview ready" });
      return result;
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function importSources(sources: string, topic: string) {
    setBusy(true);
    setNotice(null);
    try {
      const result = await importDeskSources(sources, topic);
      setSourceImportResult(result);
      await refresh();
      try {
        await refreshDeskSources();
      } catch (error) {
        setDeskSourcesError(errorMessage(error));
      }
      setNotice({ tone: "success", text: result.detail || result.title || "Sources saved" });
      return result;
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function setSourceEnabled(sourceId: string, enabled: boolean) {
    setBusy(true);
    setNotice(null);
    try {
      const sources = await setDeskSourceEnabledRequest(sourceId, enabled);
      setDeskSources(sources);
      setDeskSourcesError(null);
      await refresh();
      setNotice({ tone: "success", text: enabled ? "Source enabled" : "Source paused" });
    } catch (error) {
      const message = errorMessage(error);
      setDeskSourcesError(message);
      setNotice({ tone: "error", text: message });
    } finally {
      setBusy(false);
    }
  }

  async function setSourceTopics(sourceId: string, topics: string[]) {
    setBusy(true);
    setNotice(null);
    try {
      const sources = await setDeskSourceTopicsRequest(sourceId, topics);
      setDeskSources(sources);
      setDeskSourcesError(null);
      await refresh();
      setNotice({ tone: "success", text: "Source topics saved" });
    } catch (error) {
      const message = errorMessage(error);
      setDeskSourcesError(message);
      setNotice({ tone: "error", text: message });
      throw error;
    } finally {
      setBusy(false);
    }
  }

  async function pullLatest() {
    if (!gitStatus?.pull_allowed) {
      return;
    }
    const confirmed = window.confirm("Pull latest with git pull --ff-only? Local changes must already be clean.");
    if (!confirmed) {
      return;
    }
    setGitBusy(true);
    setNotice(null);
    try {
      const git = await pullLatestGit();
      setGitStatus(git);
      setNotice({ tone: "success", text: "Pulled latest upstream changes" });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setGitBusy(false);
    }
  }

  async function executeDeskAction(actionId: string, body: Record<string, unknown> = {}) {
    if (actionId === "schedule_install_dry_run") {
      body.confirm = true;
    }
    if (actionId === "schedule_remove_dry_run") {
      body.confirm = true;
    }
    try {
      const result = await runAction(actionId, body);
      if (actionId === "schedule_install_dry_run" || actionId === "schedule_remove_dry_run") {
        await refreshDeskSchedulerStatus().catch((error) => setDeskSchedulerError(errorMessage(error)));
      }
      if (result.status === "success") {
        await refresh();
        setNotice({ tone: "success", text: result.title });
        return;
      }
      setNotice({ tone: result.status === "needs_human" ? "success" : "error", text: result.title });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    }
  }

  async function runDeskAction(actionId: string) {
    setNotice(null);
    if (actionId === "live_delivery_human") {
      setActiveTab("settings");
      setSettingsFocusTarget("notifications");
      setNotice({ tone: "success", text: "Opened notification settings" });
      return;
    }
    const confirmation = deskActionConfirmation(actionId);
    if (confirmation) {
      pendingDeskActionReturnFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      setPendingDeskAction(confirmation);
      return;
    }
    await executeDeskAction(actionId);
  }

  const cancelPendingDeskAction = useCallback(() => {
    setPendingDeskAction(null);
  }, []);

  const clearSettingsFocusTarget = useCallback(() => {
    setSettingsFocusTarget(null);
  }, []);

  const confirmPendingDeskAction = useCallback(() => {
    setPendingDeskAction((confirmation) => {
      if (confirmation) {
        void executeDeskAction(confirmation.actionId);
      }
      return null;
    });
  }, []);

  return (
    <main className="app-shell" data-testid="tgcs-dashboard">
      <div className="pixel-grid" aria-hidden="true" />
      <ConsoleHeader busy={busy || Boolean(busyActionId) || Boolean(deskTelegram.busy)} onRefresh={refreshNow} />

      {(notice || loadError) && (
        <div className={`notice ${notice?.tone === "error" || loadError ? "error" : "success"}`} role="status">
          {loadError || notice?.text}
        </div>
      )}

      <section className="workbench">
        <NavigationRail tabs={tabShell} activeTab={activeTab} tabCounts={tabCounts} setActiveTab={setActiveTab} />

        <section className="main-board" aria-label={boardMeta.title}>
          <WorkbenchHeader meta={boardMeta} />
          {showBoardStatusStack && (
            <div className="board-status-stack" aria-label="Board status summary">
              {showCommandStrip && <CommandStrip state={state} metrics={metrics} />}
              {showOpportunitySummary && <OpportunitySummaryPanel summary={state.opportunity_summary} />}
              <ValidationSummaryPanel summary={showValidationSummary ? state.validation_summary : undefined} />
            </div>
          )}
          <div className="board-body">
            {activeTab === "inbox" && (
              <InboxView
                cards={state.inbox}
                latestRunId={latestRunId}
                setupStatus={state.setup_status}
                profileReportNames={profileReportNames}
                act={act}
                busy={busy}
              />
            )}
            {activeTab === "actions" && (
              <ActionsView
                actions={deskActions}
                results={deskActionResults}
                busyActionId={busyActionId}
                loadError={deskActionsLoadError || deskActionRunError || deskSchedulerError || ""}
                setupStatus={state.setup_status}
                scheduler={deskSchedulerStatus}
                targets={state.delivery_targets}
                telegram={{
                  status: deskTelegram.status,
                  busy: deskTelegram.busy,
                  error: deskTelegram.error,
                  saveCredentials: deskTelegram.saveCredentials,
                  sendCode: deskTelegram.sendCode,
                  verifyCode: deskTelegram.verifyCode,
                  refresh: deskTelegram.refreshTelegram,
                  cancelLogin: deskTelegram.cancelLogin,
                }}
                onRun={runDeskAction}
              />
            )}
            {activeTab === "profiles" && (
              <ProfilesView
                profiles={state.profiles}
                patches={state.profile_patch_suggestions}
                applyPatch={applyPatch}
                revertPatch={revertPatch}
                setAlertMode={setAlertMode}
                setProfileEnabled={setProfileEnabled}
                setProfileRuntimeSettings={setProfileRuntimeSettings}
                busy={busy}
              />
            )}
            {activeTab === "runs" && <RunsView runs={state.runs} />}
            {activeTab === "settings" && (
              <>
                <SettingsView
                  targets={state.delivery_targets}
                  sourceStats={state.source_stats}
                  sourceInsights={state.source_insights}
                  feedbackSummary={state.feedback_summary}
                  feedbackExport={feedbackExport}
                  exportFeedback={exportFeedback}
                  clearFeedback={clearFeedback}
                  undoFeedbackDecision={undoFeedbackDecision}
                  runAgainWithLearning={() => void runDeskAction("monitor_jobs_dry_run")}
                  deliveryTest={deliveryTest}
                  notificationTokenStatus={notificationTokenStatus}
                  notificationTokenError={notificationTokenError}
                  sourceLibrary={deskSources}
                  sourceLibraryError={deskSourcesError}
                  sourceImportResult={sourceImportResult}
                  saveDeliveryTarget={saveDeliveryTarget}
                  saveNotificationToken={saveNotificationToken}
                  clearNotificationToken={clearNotificationToken}
                  testDeliveryTarget={testDeliveryTarget}
                  previewSourceImport={previewSourceImport}
                  importSources={importSources}
                  setSourceEnabled={setSourceEnabled}
                  setSourceTopics={setSourceTopics}
                  busy={busy}
                  focusTarget={settingsFocusTarget}
                  onFocusHandled={clearSettingsFocusTarget}
                />
                <StatusRail
                  gitStatus={gitStatus}
                  gitBusy={gitBusy}
                  onCheckUpdates={checkUpdates}
                  onPullLatest={pullLatest}
                />
              </>
            )}
          </div>
        </section>
      </section>
      {pendingDeskAction && (
        <DeskActionConfirmDialog
          confirmation={pendingDeskAction}
          returnFocusRef={pendingDeskActionReturnFocus}
          busy={Boolean(busyActionId)}
          onCancel={cancelPendingDeskAction}
          onConfirm={confirmPendingDeskAction}
        />
      )}
    </main>
  );
}

function deskActionConfirmation(actionId: string): DeskActionConfirmation | null {
  if (actionId === "schedule_install_dry_run") {
    return {
      actionId,
      title: "Turn on dry-run checks?",
      detail: "Signal Desk will run local dry-run checks every 15 minutes in the background. No live Telegram alerts will be sent.",
      confirmLabel: "Turn on dry-run checks",
    };
  }
  if (actionId === "schedule_remove_dry_run") {
    return {
      actionId,
      title: "Turn off dry-run checks?",
      detail: "Background dry-run checks will stop. Manual scans in Signal Desk will still work.",
      confirmLabel: "Turn off dry-run checks",
    };
  }
  return null;
}

function DeskActionConfirmDialog({
  busy,
  confirmation,
  onCancel,
  onConfirm,
  returnFocusRef,
}: {
  busy: boolean;
  confirmation: DeskActionConfirmation;
  onCancel: () => void;
  onConfirm: () => void;
  returnFocusRef: MutableRefObject<HTMLElement | null>;
}) {
  const cancelButtonRef = useRef<HTMLButtonElement | null>(null);
  const dialogRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    cancelButtonRef.current?.focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onCancel();
        return;
      }
      if (event.key !== "Tab") {
        return;
      }
      const focusable = Array.from(dialogRef.current?.querySelectorAll<HTMLButtonElement>("button:not(:disabled)") ?? []);
      if (!focusable.length) {
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
      const restoreFocusTarget = returnFocusRef.current;
      returnFocusRef.current = null;
      window.setTimeout(() => restoreFocusTarget?.focus(), 0);
    };
  }, [onCancel, returnFocusRef]);

  return (
    <div className="desk-confirm-backdrop" onClick={(event) => event.currentTarget === event.target && onCancel()} role="presentation">
      <section
        className="desk-confirm-dialog"
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="desk-confirm-title"
        aria-describedby="desk-confirm-detail"
      >
        <div>
          <span className="panel-kicker">Confirm automation</span>
          <h2 id="desk-confirm-title">{confirmation.title}</h2>
          <p id="desk-confirm-detail">{confirmation.detail}</p>
        </div>
        <div className="desk-confirm-actions">
          <button className="journey-button secondary" disabled={busy} onClick={onCancel} ref={cancelButtonRef} type="button">
            Cancel
          </button>
          <button className="journey-button" disabled={busy} onClick={onConfirm} type="button">
            {confirmation.confirmLabel}
          </button>
        </div>
      </section>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
