import { StrictMode, useEffect, useMemo, useState, type CSSProperties, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import {
  Activity,
  AlertTriangle,
  Ban,
  Check,
  Clock3,
  Download,
  FileDiff,
  GitBranch,
  Inbox,
  Play,
  RefreshCw,
  Settings,
  ShieldCheck,
  UserRoundCog,
  X,
} from "lucide-react";
import signalIcon from "./assets/tgcs-signal-icon.png";
import "./styles.css";

type SourceRef = {
  channel: string;
  id: string | number;
};

type DecisionState = {
  status?: string;
  signals?: string[];
  explanations?: Record<string, string>;
};

type ReviewCard = {
  schema_version: "review_card_v1";
  card_id: string;
  profile_id: string;
  title: string;
  rating: string;
  decision_status: string;
  source_refs: SourceRef[];
  item: {
    why?: string;
    decision_state?: DecisionState;
  };
  status: string;
  report_path?: string;
  dashboard_url?: string;
  updated_at: string;
};

type Profile = {
  profile_id: string;
  path: string;
  enabled: boolean;
  config: Record<string, unknown>;
  updated_at: string;
};

type RunArtifact = {
  type?: string;
  path: string;
  sha256?: string;
};

type Run = {
  run_id: string;
  profile_id: string;
  status: string;
  started_at: string;
  completed_at?: string;
  manifest: {
    alert_count?: number;
    review_card_count?: number;
    artifacts?: RunArtifact[];
  };
};

type DeliveryTarget = {
  target_id: string;
  type: string;
  enabled: boolean;
  config: Record<string, unknown>;
  updated_at: string;
};

type ProfilePatch = {
  patch_id: string;
  profile_id: string;
  card_id?: string;
  note: string;
  status: string;
  diff_text: string;
  created_at: string;
  applied_at?: string;
};

type DashboardState = {
  schema_version?: "dashboard_state_v1";
  profiles: Profile[];
  inbox: ReviewCard[];
  runs: Run[];
  delivery_targets: DeliveryTarget[];
  profile_patch_suggestions: ProfilePatch[];
};

type Tab = "inbox" | "profiles" | "runs" | "settings";

type Metric = {
  label: string;
  value: string;
  detail: string;
  tone: "amber" | "teal" | "rust" | "blue";
};

type GitUpdateStatus = {
  schema_version: "git_update_status_v1";
  status: string;
  message: string;
  branch: string;
  upstream?: string | null;
  repo_url?: string | null;
  head?: string | null;
  remote_head?: string | null;
  ahead: number;
  behind: number;
  dirty: boolean;
  dirty_count: number;
  pull_allowed: boolean;
  checked_at: string;
};

const emptyState: DashboardState = {
  profiles: [],
  inbox: [],
  runs: [],
  delivery_targets: [],
  profile_patch_suggestions: [],
};

const projectRepoUrl = "https://github.com/Sapientropic/tg-channel-scanner";

const tabShell: Array<{ tab: Tab; icon: ReactNode; label: string }> = [
  { tab: "inbox", icon: <Inbox size={17} />, label: "Inbox" },
  { tab: "profiles", icon: <UserRoundCog size={17} />, label: "Profiles" },
  { tab: "runs", icon: <Play size={17} />, label: "Runs" },
  { tab: "settings", icon: <Settings size={17} />, label: "Settings" },
];

function App() {
  const { state, refresh, loadError } = useDashboardState();
  const [activeTab, setActiveTab] = useState<Tab>("inbox");
  const [busy, setBusy] = useState(false);
  const [gitBusy, setGitBusy] = useState(false);
  const [gitStatus, setGitStatus] = useState<GitUpdateStatus | null>(null);
  const [notice, setNotice] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  const metrics = useMemo(() => buildMetrics(state), [state]);
  const tabCounts = buildTabCounts(state);
  const boardMeta = buildBoardMeta(activeTab, state);

  async function refreshNow() {
    setBusy(true);
    try {
      await refresh();
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
      const response = await fetch(`/api/review-cards/${encodeURIComponent(cardId)}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, note }),
      });
      await assertOk(response);
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
      const response = await fetch(`/api/profile-patches/${encodeURIComponent(patchId)}/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      await assertOk(response);
      await refresh();
      setNotice({ tone: "success", text: "Profile snapshot saved and diff applied" });
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
      const response = await fetch("/api/git/check-updates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      const payload = await readJson(response);
      setGitStatus(payload.git as GitUpdateStatus);
      setNotice({ tone: "success", text: "Remote status checked" });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setGitBusy(false);
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
      const response = await fetch("/api/git/pull-latest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirm: true }),
      });
      const payload = await readJson(response);
      setGitStatus(payload.git as GitUpdateStatus);
      setNotice({ tone: "success", text: "Pulled latest upstream changes" });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setGitBusy(false);
    }
  }

  return (
    <main className="app-shell" data-testid="tgcs-dashboard">
      <div className="pixel-grid" aria-hidden="true" />
      <header className="console-header">
        <div className="brand-station">
          <a
            className="pixel-mark"
            href={projectRepoUrl}
            target="_blank"
            rel="noreferrer"
            aria-label="Open TGCS Git repository"
            title="Open Git repository"
          >
            <img src={signalIcon} alt="" />
          </a>
          <div className="brand-copy">
            <p className="eyebrow">TG Channel Scanner</p>
            <h1>Signal Desk</h1>
            <div className="header-readout" aria-label="Local dashboard boundary">
              <span>SQLite local</span>
              <span>127.0.0.1</span>
              <span>raw text redacted</span>
            </div>
          </div>
        </div>
        <button className="refresh-button" onClick={refreshNow} disabled={busy} title="Refresh state" type="button">
          <RefreshCw size={18} className={busy ? "spin" : ""} />
          <span>Refresh</span>
        </button>
      </header>

      <CommandStrip state={state} metrics={metrics} />

      {(notice || loadError) && (
        <div className={`notice ${notice?.tone === "error" || loadError ? "error" : "success"}`} role="status">
          {loadError || notice?.text}
        </div>
      )}

      <section className="workbench">
        <aside className="nav-rail" aria-label="Dashboard navigation">
          <nav className="tabs" aria-label="Dashboard tabs">
            {tabShell.map((tab) => (
              <TabButton
                key={tab.tab}
                {...tab}
                active={activeTab}
                count={tabCounts[tab.tab]}
                setActive={setActiveTab}
              />
            ))}
          </nav>
          <div className="rail-note">
            <ShieldCheck size={16} />
            <span>Tokens stay outside SQLite</span>
          </div>
        </aside>

        <section className="main-board" aria-label={boardMeta.title}>
          <WorkbenchHeader meta={boardMeta} />
          <div className="board-body">
            {activeTab === "inbox" && <InboxView cards={state.inbox} act={act} busy={busy} />}
            {activeTab === "profiles" && (
              <ProfilesView
                profiles={state.profiles}
                patches={state.profile_patch_suggestions}
                applyPatch={applyPatch}
                busy={busy}
              />
            )}
            {activeTab === "runs" && <RunsView runs={state.runs} />}
            {activeTab === "settings" && <SettingsView targets={state.delivery_targets} />}
          </div>
        </section>

        <StatusRail
          gitStatus={gitStatus}
          gitBusy={gitBusy}
          onCheckUpdates={checkUpdates}
          onPullLatest={pullLatest}
        />
      </section>
    </main>
  );
}

function useDashboardState() {
  const [state, setState] = useState<DashboardState>(emptyState);
  const [loadError, setLoadError] = useState("");

  async function load(signal?: AbortSignal) {
    const response = await fetch("/api/state", { signal });
    await assertOk(response);
    const payload = (await response.json()) as Partial<DashboardState>;
    setState(sanitizeDashboardState(payload));
    setLoadError("");
  }

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal).catch((error) => {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }
      setLoadError(errorMessage(error));
      setState(emptyState);
    });
    return () => controller.abort();
  }, []);

  return { state, refresh: () => load(), loadError };
}

function sanitizeDashboardState(payload: Partial<DashboardState>): DashboardState {
  return {
    schema_version: payload.schema_version,
    profiles: Array.isArray(payload.profiles) ? payload.profiles : [],
    inbox: Array.isArray(payload.inbox) ? payload.inbox : [],
    runs: Array.isArray(payload.runs) ? payload.runs : [],
    delivery_targets: Array.isArray(payload.delivery_targets) ? payload.delivery_targets : [],
    profile_patch_suggestions: Array.isArray(payload.profile_patch_suggestions)
      ? payload.profile_patch_suggestions
      : [],
  };
}

function CommandStrip({ state, metrics }: { state: DashboardState; metrics: Metric[] }) {
  const pulseWidth = Math.min(100, Math.max(8, state.inbox.length * 18));
  return (
    <section className="command-strip" aria-label="Dashboard status">
      <div className="pulse-panel">
        <span className="panel-kicker">Queue Pulse</span>
        <strong>{state.inbox.length}</strong>
        <small>{state.inbox.length ? "cards need review" : "queue clear"}</small>
        <div className="pulse-meter" style={{ "--pulse": `${pulseWidth}%` } as CSSProperties} aria-hidden="true">
          <span />
        </div>
      </div>
      <div className="metric-grid">
        {metrics.map((metric) => (
          <MetricTile key={metric.label} metric={metric} />
        ))}
      </div>
    </section>
  );
}

function TabButton({
  tab,
  active,
  count,
  setActive,
  icon,
  label,
}: {
  tab: Tab;
  active: Tab;
  count: number;
  setActive: (tab: Tab) => void;
  icon: ReactNode;
  label: string;
}) {
  return (
    <button className={active === tab ? "tab active" : "tab"} onClick={() => setActive(tab)} type="button">
      <span className="tab-icon">{icon}</span>
      <span className="tab-label">{label}</span>
      <span className="tab-count">{count}</span>
    </button>
  );
}

function MetricTile({ metric }: { metric: Metric }) {
  return (
    <article className={`metric-tile ${metric.tone}`}>
      <span>{metric.label}</span>
      <strong>{metric.value}</strong>
      <small>{metric.detail}</small>
    </article>
  );
}

function WorkbenchHeader({
  meta,
}: {
  meta: {
    title: string;
    detail: string;
    value: string;
    tone: "amber" | "teal" | "rust" | "blue";
  };
}) {
  return (
    <header className="board-header">
      <div>
        <p className="eyebrow">Workspace</p>
        <h2>{meta.title}</h2>
        <span>{meta.detail}</span>
      </div>
      <strong className={`board-token ${meta.tone}`}>{meta.value}</strong>
    </header>
  );
}

function InboxView({
  cards,
  act,
  busy,
}: {
  cards: ReviewCard[];
  act: (cardId: string, action: string, note?: string) => void;
  busy: boolean;
}) {
  if (!cards.length) {
    return (
      <EmptyState
        icon={<Inbox size={24} />}
        title="Inbox clear"
        detail="SQLite connected. Pending review cards are currently zero."
      />
    );
  }
  return (
    <section className="list-section" aria-label="Pending review cards">
      {cards.map((card) => (
        <article className={`review-card rating-${toneClass(card.rating)}`} key={card.card_id}>
          <div className="card-spine" aria-hidden="true">
            <span>{card.rating}</span>
          </div>
          <div className="card-main">
            <div className="card-title-row">
              <h3>{card.title}</h3>
              <span className={`rating ${toneClass(card.rating)}`}>{card.rating}</span>
            </div>
            <p className="reason">{card.item.why || "Decision reason unavailable."}</p>
            <div className="meta-row">
              <span>{card.profile_id}</span>
              <span>{card.decision_status}</span>
              <span>{formatDate(card.updated_at)}</span>
            </div>
            <SourceRefs refs={card.source_refs} />
            {card.report_path && <code className="report-path">{card.report_path}</code>}
          </div>
          <CardActions card={card} act={act} busy={busy} />
        </article>
      ))}
    </section>
  );
}

function CardActions({
  card,
  act,
  busy,
}: {
  card: ReviewCard;
  act: (cardId: string, action: string, note?: string) => void;
  busy: boolean;
}) {
  const [note, setNote] = useState("");
  return (
    <div className="card-actions">
      <div className="action-cluster" aria-label="Review actions">
        <button title="Keep" type="button" onClick={() => act(card.card_id, "keep")} disabled={busy}>
          <Check size={16} />
          <span>Keep</span>
        </button>
        <button title="Skip" type="button" onClick={() => act(card.card_id, "skip")} disabled={busy}>
          <X size={16} />
          <span>Skip</span>
        </button>
        <button
          title="False positive"
          type="button"
          onClick={() => act(card.card_id, "false_positive")}
          disabled={busy}
        >
          <Ban size={16} />
          <span>False</span>
        </button>
      </div>
      <label className="follow-up">
        <span>Profile note</span>
        <div className="follow-up-control">
          <textarea
            aria-label="Follow-up note"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Add profile preference"
            disabled={busy}
          />
          <button
            title="Create profile diff"
            type="button"
            onClick={() => act(card.card_id, "follow_up", note)}
            disabled={busy}
          >
            <FileDiff size={16} />
          </button>
        </div>
      </label>
    </div>
  );
}

function ProfilesView({
  profiles,
  patches,
  applyPatch,
  busy,
}: {
  profiles: Profile[];
  patches: ProfilePatch[];
  applyPatch: (patchId: string) => void;
  busy: boolean;
}) {
  return (
    <section className="split-section">
      <div className="plain-panel">
        <PanelHeader icon={<UserRoundCog size={18} />} title="Profiles" count={profiles.length} />
        {profiles.length ? (
          <div className="table-list">
            {profiles.map((profile) => (
              <div className="table-row profile-row" key={profile.profile_id}>
                <strong>{profile.profile_id}</strong>
                <span className={profile.enabled ? "status enabled" : "status disabled"}>
                  {profile.enabled ? "enabled" : "disabled"}
                </span>
                <code>{profile.path}</code>
              </div>
            ))}
          </div>
        ) : (
          <InlineEmpty title="No profiles registered" />
        )}
      </div>
      <div className="plain-panel">
        <PanelHeader icon={<FileDiff size={18} />} title="Profile Diffs" count={patches.length} />
        {patches.length ? (
          <div className="patch-list">
            {patches.map((patch) => (
              <article className="review-card patch-card" key={patch.patch_id}>
                <div className="card-main">
                  <div className="card-title-row">
                    <h3>{patch.profile_id}</h3>
                    <span className={`status ${toneClass(patch.status)}`}>{patch.status}</span>
                  </div>
                  <p className="note-line">{patch.note || "Follow-up preference draft"}</p>
                  <pre>{patch.diff_text || "No diff body recorded."}</pre>
                  {patch.status === "pending" && (
                    <button
                      className="text-button"
                      type="button"
                      onClick={() => applyPatch(patch.patch_id)}
                      disabled={busy}
                    >
                      Apply
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <InlineEmpty title="No pending profile diffs" />
        )}
      </div>
    </section>
  );
}

function RunsView({ runs }: { runs: Run[] }) {
  if (!runs.length) {
    return <EmptyState icon={<Clock3 size={24} />} title="No runs yet" detail="Run history is empty in this database." />;
  }
  return (
    <section className="table-section" aria-label="Run history">
      <PanelHeader icon={<Activity size={18} />} title="Runs" count={runs.length} />
      <div className="table-list">
        {runs.map((run) => (
          <div className="table-row run-row" key={run.run_id}>
            <strong>{run.profile_id}</strong>
            <span className={`status ${toneClass(run.status)}`}>{run.status}</span>
            <span>{run.manifest.review_card_count ?? 0} cards</span>
            <span>{run.manifest.alert_count ?? 0} alerts</span>
            <code>{shortId(run.run_id)}</code>
            <code>{formatArtifactPath(run.manifest.artifacts)}</code>
          </div>
        ))}
      </div>
    </section>
  );
}

function SettingsView({ targets }: { targets: DeliveryTarget[] }) {
  return (
    <section className="table-section" aria-label="Delivery settings">
      <PanelHeader icon={<Settings size={18} />} title="Delivery Targets" count={targets.length} />
      {targets.length ? (
        <div className="table-list">
          {targets.map((target) => (
            <div className="table-row target-row" key={target.target_id}>
              <strong>{target.target_id}</strong>
              <span>{target.type}</span>
              <span className={target.enabled ? "status enabled" : "status disabled"}>
                {target.enabled ? "enabled" : "disabled"}
              </span>
              <code>{String(target.config.chat_id || "chat unset")}</code>
            </div>
          ))}
        </div>
      ) : (
        <InlineEmpty title="No delivery targets registered" />
      )}
    </section>
  );
}

function StatusRail({
  gitStatus,
  gitBusy,
  onCheckUpdates,
  onPullLatest,
}: {
  gitStatus: GitUpdateStatus | null;
  gitBusy: boolean;
  onCheckUpdates: () => void;
  onPullLatest: () => void;
}) {
  return (
    <aside className="context-rail" aria-label="Repository update controls">
      <RailPanel icon={<GitBranch size={18} />} title="Repository">
        <StatusLine label="Branch" value={gitStatus?.branch || "unchecked"} />
        <StatusLine label="Remote" value={formatGitRemoteState(gitStatus)} />
        {gitStatus && <StatusLine label="Delta" value={`${gitStatus.ahead} ahead / ${gitStatus.behind} behind`} />}
        <div className="git-actions">
          <button type="button" onClick={onCheckUpdates} disabled={gitBusy}>
            <GitBranch size={15} />
            <span>{gitBusy ? "Checking" : "Check updates"}</span>
          </button>
          <button type="button" onClick={onPullLatest} disabled={gitBusy || !gitStatus?.pull_allowed}>
            <Download size={15} />
            <span>Pull latest</span>
          </button>
        </div>
        <p className={`git-message ${gitStatus?.status || "unchecked"}`}>
          {gitStatus ? gitStatus.message : "Check remote status before pulling."}
        </p>
      </RailPanel>
    </aside>
  );
}

function RailPanel({ icon, title, children }: { icon: ReactNode; title: string; children: ReactNode }) {
  return (
    <section className="rail-panel">
      <PanelHeader icon={icon} title={title} />
      <div className="rail-body">{children}</div>
    </section>
  );
}

function PanelHeader({ icon, title, count }: { icon: ReactNode; title: string; count?: number }) {
  return (
    <header className="panel-header">
      <span className="panel-title">
        {icon}
        {title}
      </span>
      {typeof count === "number" && <span className="count-badge">{count}</span>}
    </header>
  );
}

function StatusLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="status-line">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EmptyState({ icon, title, detail }: { icon: ReactNode; title: string; detail?: string }) {
  return (
    <section className="empty-state">
      <div className="empty-radar" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <div className="empty-icon">{icon}</div>
      <div className="empty-copy">
        <h3>{title}</h3>
        {detail && <p>{detail}</p>}
      </div>
      <div className="empty-readout" aria-label="Empty state readout">
        <StatusLine label="DB" value="online" />
        <StatusLine label="Queue" value="0 pending" />
        <StatusLine label="Mode" value="local" />
      </div>
    </section>
  );
}

function InlineEmpty({ title }: { title: string }) {
  return (
    <div className="inline-empty">
      <AlertTriangle size={16} />
      <span>{title}</span>
    </div>
  );
}

function SourceRefs({ refs }: { refs: SourceRef[] }) {
  if (!refs.length) {
    return (
      <div className="source-row">
        <span className="source-chip muted">source refs unavailable</span>
      </div>
    );
  }
  return (
    <div className="source-row" aria-label="Source references">
      {refs.slice(0, 4).map((ref) => (
        <span className="source-chip" key={`${ref.channel}-${ref.id}`}>
          {ref.channel}#{ref.id}
        </span>
      ))}
      {refs.length > 4 && <span className="source-chip muted">+{refs.length - 4}</span>}
    </div>
  );
}

function buildMetrics(state: DashboardState): Metric[] {
  const activeProfiles = state.profiles.filter((profile) => profile.enabled).length;
  const totalAlerts = state.runs.reduce((sum, run) => sum + (run.manifest.alert_count ?? 0), 0);
  const pendingPatches = state.profile_patch_suggestions.filter((patch) => patch.status === "pending").length;
  const activeTargets = state.delivery_targets.filter((target) => target.enabled).length;

  return [
    { label: "Runs", value: String(state.runs.length), detail: latestRunDetail(state.runs), tone: "teal" },
    { label: "Alerts", value: String(totalAlerts), detail: `${activeTargets} target${activeTargets === 1 ? "" : "s"}`, tone: "rust" },
    { label: "Profiles", value: String(activeProfiles), detail: `${pendingPatches} diff${pendingPatches === 1 ? "" : "s"}`, tone: "blue" },
  ];
}

function buildTabCounts(state: DashboardState): Record<Tab, number> {
  return {
    inbox: state.inbox.length,
    profiles: state.profiles.length,
    runs: state.runs.length,
    settings: state.delivery_targets.length,
  };
}

function buildBoardMeta(activeTab: Tab, state: DashboardState) {
  const metas: Record<Tab, { title: string; detail: string; value: string; tone: "amber" | "teal" | "rust" | "blue" }> = {
    inbox: {
      title: "Review Queue",
      detail: state.inbox.length ? "Pending review cards sorted by latest signal." : "Queue is clear in the current database.",
      value: `${state.inbox.length}`,
      tone: "amber",
    },
    profiles: {
      title: "Profile Control",
      detail: `${state.profiles.filter((profile) => profile.enabled).length} enabled profiles, ${
        state.profile_patch_suggestions.filter((patch) => patch.status === "pending").length
      } pending diffs.`,
      value: `${state.profiles.length}`,
      tone: "blue",
    },
    runs: {
      title: "Run Ledger",
      detail: state.runs.length ? `Latest run started ${formatDate(state.runs[0].started_at)}.` : "Run history is empty.",
      value: `${state.runs.length}`,
      tone: "teal",
    },
    settings: {
      title: "Delivery Matrix",
      detail: `${state.delivery_targets.filter((target) => target.enabled).length} active delivery targets.`,
      value: `${state.delivery_targets.length}`,
      tone: "rust",
    },
  };
  return metas[activeTab];
}

function latestRunDetail(runs: Run[]) {
  if (!runs.length) {
    return "no history";
  }
  return formatDate(runs[0].started_at);
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

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}

function toneClass(value: string) {
  const normalized = value.toLowerCase().replace(/[^a-z0-9_-]+/g, "-");
  return normalized || "unknown";
}

function shortId(value: string) {
  if (value.length <= 18) {
    return value;
  }
  return `${value.slice(0, 10)}...${value.slice(-6)}`;
}

function formatDate(value?: string) {
  if (!value) {
    return "unknown";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())} ${pad(parsed.getHours())}:${pad(parsed.getMinutes())}`;
}

function formatArtifactPath(artifacts?: RunArtifact[]) {
  if (!artifacts?.length) {
    return "artifact unset";
  }
  const report = artifacts.find((artifact) => artifact.type?.includes("report")) ?? artifacts[0];
  return report.path;
}

function formatGitRemoteState(status: GitUpdateStatus | null) {
  if (!status) {
    return "unchecked";
  }
  if (status.dirty) {
    return `dirty ${status.dirty_count}`;
  }
  return status.status.replace(/_/g, " ");
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
