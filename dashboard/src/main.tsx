import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import {
  Bell,
  Check,
  Clock3,
  FileDiff,
  Inbox,
  Play,
  RefreshCw,
  Settings,
  UserRoundCog,
  X,
} from "lucide-react";
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
  updated_at: string;
};

type Profile = {
  profile_id: string;
  path: string;
  enabled: boolean;
  config: Record<string, unknown>;
  updated_at: string;
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
    artifacts?: Array<{ type: string; path: string }>;
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
  profiles: Profile[];
  inbox: ReviewCard[];
  runs: Run[];
  delivery_targets: DeliveryTarget[];
  profile_patch_suggestions: ProfilePatch[];
};

type Tab = "inbox" | "profiles" | "runs" | "settings";

const emptyState: DashboardState = {
  profiles: [],
  inbox: [],
  runs: [],
  delivery_targets: [],
  profile_patch_suggestions: [],
};

function App() {
  const [state, setState] = useDashboardState();
  const [activeTab, setActiveTab] = useState<Tab>("inbox");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setBusy(true);
    try {
      const response = await fetch("/api/state");
      setState(await response.json());
    } finally {
      setBusy(false);
    }
  }

  async function act(cardId: string, action: string, note = "") {
    setBusy(true);
    try {
      await fetch(`/api/review-cards/${encodeURIComponent(cardId)}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, note }),
      });
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  async function applyPatch(patchId: string) {
    setBusy(true);
    try {
      await fetch(`/api/profile-patches/${encodeURIComponent(patchId)}/apply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">TG Channel Scanner</p>
          <h1>Review Inbox</h1>
        </div>
        <button className="icon-button" onClick={refresh} disabled={busy} title="Refresh">
          <RefreshCw size={18} />
        </button>
      </header>

      <nav className="tabs" aria-label="Dashboard tabs">
        <TabButton tab="inbox" active={activeTab} setActive={setActiveTab} icon={<Inbox size={17} />} label="Inbox" />
        <TabButton
          tab="profiles"
          active={activeTab}
          setActive={setActiveTab}
          icon={<UserRoundCog size={17} />}
          label="Profiles"
        />
        <TabButton tab="runs" active={activeTab} setActive={setActiveTab} icon={<Play size={17} />} label="Runs" />
        <TabButton
          tab="settings"
          active={activeTab}
          setActive={setActiveTab}
          icon={<Settings size={17} />}
          label="Settings"
        />
      </nav>

      {activeTab === "inbox" && <InboxView cards={state.inbox} act={act} />}
      {activeTab === "profiles" && (
        <ProfilesView profiles={state.profiles} patches={state.profile_patch_suggestions} applyPatch={applyPatch} />
      )}
      {activeTab === "runs" && <RunsView runs={state.runs} />}
      {activeTab === "settings" && <SettingsView targets={state.delivery_targets} />}
    </main>
  );
}

function useDashboardState(): [DashboardState, (value: DashboardState) => void] {
  const [state, setState] = useState<DashboardState>(emptyState);
  useEffect(() => {
    let mounted = true;
    fetch("/api/state")
      .then((response) => response.json())
      .then((payload) => {
        if (mounted) {
          setState({ ...emptyState, ...payload });
        }
      })
      .catch(() => {
        if (mounted) {
          setState(emptyState);
        }
      });
    return () => {
      mounted = false;
    };
  }, []);
  return [state, setState];
}

function TabButton({
  tab,
  active,
  setActive,
  icon,
  label,
}: {
  tab: Tab;
  active: Tab;
  setActive: (tab: Tab) => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button className={active === tab ? "tab active" : "tab"} onClick={() => setActive(tab)} type="button">
      {icon}
      <span>{label}</span>
    </button>
  );
}

function InboxView({ cards, act }: { cards: ReviewCard[]; act: (cardId: string, action: string, note?: string) => void }) {
  if (!cards.length) {
    return <EmptyState icon={<Inbox size={22} />} title="Inbox clear" />;
  }
  return (
    <section className="list-section">
      {cards.map((card) => (
        <article className="item-card" key={card.card_id}>
          <div className="card-main">
            <div className="card-title-row">
              <h2>{card.title}</h2>
              <span className={`rating ${card.rating}`}>{card.rating}</span>
            </div>
            <p className="reason">{card.item.why || "Decision reason unavailable."}</p>
            <div className="meta-row">
              <span>{card.profile_id}</span>
              <span>{card.decision_status}</span>
              <span>{formatRefs(card.source_refs)}</span>
            </div>
          </div>
          <CardActions card={card} act={act} />
        </article>
      ))}
    </section>
  );
}

function CardActions({ card, act }: { card: ReviewCard; act: (cardId: string, action: string, note?: string) => void }) {
  const [note, setNote] = useState("");
  return (
    <div className="card-actions">
      <button title="Keep" type="button" onClick={() => act(card.card_id, "keep")}>
        <Check size={16} />
      </button>
      <button title="Skip" type="button" onClick={() => act(card.card_id, "skip")}>
        <X size={16} />
      </button>
      <button title="False positive" type="button" onClick={() => act(card.card_id, "false_positive")}>
        <Bell size={16} />
      </button>
      <div className="follow-up">
        <textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Follow-up note" />
        <button title="Create profile diff" type="button" onClick={() => act(card.card_id, "follow_up", note)}>
          <FileDiff size={16} />
        </button>
      </div>
    </div>
  );
}

function ProfilesView({
  profiles,
  patches,
  applyPatch,
}: {
  profiles: Profile[];
  patches: ProfilePatch[];
  applyPatch: (patchId: string) => void;
}) {
  return (
    <section className="split-section">
      <div className="plain-panel">
        <h2>Profiles</h2>
        <div className="table-list">
          {profiles.map((profile) => (
            <div className="table-row" key={profile.profile_id}>
              <strong>{profile.profile_id}</strong>
              <span>{profile.enabled ? "enabled" : "disabled"}</span>
              <code>{profile.path}</code>
            </div>
          ))}
        </div>
      </div>
      <div className="plain-panel">
        <h2>Profile Diffs</h2>
        <div className="patch-list">
          {patches.map((patch) => (
            <article className="item-card" key={patch.patch_id}>
              <div className="card-title-row">
                <h3>{patch.profile_id}</h3>
                <span className={`status ${patch.status}`}>{patch.status}</span>
              </div>
              <pre>{patch.diff_text}</pre>
              {patch.status === "pending" && (
                <button className="text-button" type="button" onClick={() => applyPatch(patch.patch_id)}>
                  Apply
                </button>
              )}
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function RunsView({ runs }: { runs: Run[] }) {
  if (!runs.length) {
    return <EmptyState icon={<Clock3 size={22} />} title="No runs yet" />;
  }
  return (
    <section className="table-section">
      <div className="table-list">
        {runs.map((run) => (
          <div className="table-row" key={run.run_id}>
            <strong>{run.profile_id}</strong>
            <span>{run.status}</span>
            <span>{run.manifest.review_card_count ?? 0} cards</span>
            <span>{run.manifest.alert_count ?? 0} alerts</span>
            <code>{run.run_id}</code>
          </div>
        ))}
      </div>
    </section>
  );
}

function SettingsView({ targets }: { targets: DeliveryTarget[] }) {
  return (
    <section className="table-section">
      <div className="table-list">
        {targets.map((target) => (
          <div className="table-row" key={target.target_id}>
            <strong>{target.target_id}</strong>
            <span>{target.type}</span>
            <span>{target.enabled ? "enabled" : "disabled"}</span>
            <code>{String(target.config.chat_id || "chat unset")}</code>
          </div>
        ))}
      </div>
    </section>
  );
}

function EmptyState({ icon, title }: { icon: React.ReactNode; title: string }) {
  return (
    <section className="empty-state">
      {icon}
      <h2>{title}</h2>
    </section>
  );
}

function formatRefs(refs: SourceRef[]) {
  if (!refs.length) {
    return "source refs unavailable";
  }
  return refs
    .slice(0, 3)
    .map((ref) => `${ref.channel}#${ref.id}`)
    .join(", ");
}

import React, { useEffect, useState } from "react";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
