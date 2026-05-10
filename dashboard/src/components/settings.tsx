import { useEffect, useRef, useState, type CSSProperties } from "react";
import { Activity, Bell, CircleDashed, Database, Download, Eye, Pause, Play, Save, ShieldCheck, Upload } from "lucide-react";

import { InlineEmpty, PanelHeader } from "./common";
import {
  deliveryTargetDetail,
  deliveryTargetName,
  feedbackImpactKey,
  formatActionLabel,
  metricShortLabel,
  percentWidth,
  sourceHeatClass,
  sourceSignalScore,
  toneClass,
} from "../domain/display";
import { channelDisplayName, formatPercent } from "../domain/format";
import type {
  DashboardNextAction,
  DashboardState,
  DeskSource,
  DeskSourcesResult,
  DeliveryTestResult,
  DeliveryTarget,
  FeedbackExportResult,
  FeedbackImpact,
  SourceImportResult,
  SourceInsight,
  SourceStat,
} from "../domain/types";

const SOURCE_CARD_LIMIT = 3;
const SOURCE_HEAT_LIMIT = 72;
const SOURCE_ACTION_LIMIT = 6;
const FEEDBACK_IMPACT_LIMIT = 4;

export function SettingsView({
  targets,
  sourceStats,
  sourceInsights,
  feedbackSummary,
  feedbackExport,
  exportFeedback,
  deliveryTest,
  sourceLibrary,
  sourceLibraryError,
  sourceImportResult,
  saveDeliveryTarget,
  testDeliveryTarget,
  previewSourceImport,
  importSources,
  setSourceEnabled,
  setSourceTopics,
  busy,
  focusTarget,
  onFocusHandled,
}: {
  targets: DeliveryTarget[];
  sourceStats: SourceStat[];
  sourceInsights: SourceInsight[];
  feedbackSummary?: DashboardState["feedback_summary"];
  feedbackExport: FeedbackExportResult | null;
  exportFeedback: () => void;
  deliveryTest: DeliveryTestResult | null;
  sourceLibrary: DeskSourcesResult | null;
  sourceLibraryError: string | null;
  sourceImportResult: SourceImportResult | null;
  saveDeliveryTarget: (targetId: string, chatId: string, enabled: boolean) => Promise<void>;
  testDeliveryTarget: (targetId: string, chatId: string) => Promise<void>;
  previewSourceImport: (sources: string, topic: string) => Promise<SourceImportResult>;
  importSources: (sources: string, topic: string) => Promise<SourceImportResult>;
  setSourceEnabled: (sourceId: string, enabled: boolean) => Promise<void>;
  setSourceTopics: (sourceId: string, topics: string[]) => Promise<void>;
  busy: boolean;
  focusTarget?: "notifications" | null;
  onFocusHandled?: () => void;
}) {
  const exportableCount = feedbackSummary?.exportable_count ?? feedbackExport?.feedback_count ?? 0;
  const notificationsPanelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (focusTarget !== "notifications") {
      return;
    }
    const panel = notificationsPanelRef.current;
    if (!panel) {
      return;
    }
    panel.scrollIntoView({ block: "start", behavior: "auto" });
    const target =
      panel.querySelector<HTMLElement>("input:not(:disabled), button:not(:disabled), textarea:not(:disabled), select:not(:disabled)") ?? panel;
    target.focus({ preventScroll: true });
    onFocusHandled?.();
  }, [focusTarget, onFocusHandled]);

  return (
    <section className="split-section settings-grid" aria-label="Delivery and source settings">
      <div className="table-section delivery-targets-panel" ref={notificationsPanelRef} tabIndex={-1} aria-label="Notifications">
        <PanelHeader icon={<Bell size={18} />} title="Notifications" count={targets.length} />
        {targets.length ? (
          <div className="delivery-target-list">
            {targets.map((target) => (
              <DeliveryTargetEditor
                busy={busy}
                key={target.target_id}
                saveDeliveryTarget={saveDeliveryTarget}
                target={target}
                testDeliveryTarget={testDeliveryTarget}
                testResult={deliveryTest?.target_id === target.target_id ? deliveryTest : null}
              />
            ))}
          </div>
        ) : (
          <InlineEmpty title="No notification channels set up" />
        )}
      </div>
      <SourceImportPanel
        busy={busy}
        importSources={importSources}
        previewSourceImport={previewSourceImport}
        result={sourceImportResult}
      />
      <SourceLibraryPanel
        busy={busy}
        error={sourceLibraryError}
        library={sourceLibrary}
        setSourceEnabled={setSourceEnabled}
        setSourceTopics={setSourceTopics}
      />
      <div className="table-section source-yield-panel">
        <PanelHeader icon={<Activity size={18} />} title="Yield History" count={sourceStats.length} />
        {sourceStats.length ? <SourceYieldMap sources={sourceStats} /> : <InlineEmpty title="No source stats yet" />}
      </div>
      <div className="table-section feedback-export-panel">
        <PanelHeader icon={<Download size={18} />} title="Feedback Export" count={exportableCount} />
        <FeedbackBreakdown summary={feedbackSummary} exportableCount={exportableCount} />
        {feedbackSummary?.next_action && <FeedbackNextAction action={feedbackSummary.next_action} />}
        <FeedbackFlow summary={feedbackSummary} />
        <FeedbackImpactList impacts={feedbackSummary?.recent_impacts ?? []} />
        <div className="feedback-export-row">
          <button className="text-button" type="button" onClick={exportFeedback} disabled={busy}>
            <Download size={15} />
            <span>{busy ? "Exporting" : "Export feedback file"}</span>
          </button>
          <span className="artifact-chip" title="Saved under Feedback exports">
            Feedback export file
          </span>
        </div>
      </div>
      <div className="table-section source-actions-panel">
        <PanelHeader icon={<ShieldCheck size={18} />} title="Source Actions" count={sourceInsights.length} />
        {sourceInsights.length ? <SourceActionGrid insights={sourceInsights} /> : <InlineEmpty title="No source actions yet" />}
      </div>
    </section>
  );
}

function SourceLibraryPanel({
  library,
  error,
  busy,
  setSourceEnabled,
  setSourceTopics,
}: {
  library: DeskSourcesResult | null;
  error: string | null;
  busy: boolean;
  setSourceEnabled: (sourceId: string, enabled: boolean) => Promise<void>;
  setSourceTopics: (sourceId: string, topics: string[]) => Promise<void>;
}) {
  const sources = library?.sources ?? [];
  const isLoading = !library && !error;
  const [query, setQuery] = useState("");
  const [selectedTopic, setSelectedTopic] = useState("");
  const filteredSources = filterDeskSourcesByQuery(sources, query, selectedTopic);
  const topicPreview = library?.topics.slice(0, 5) ?? [];
  const hiddenTopicCount = Math.max(0, (library?.topics.length ?? 0) - topicPreview.length);
  useEffect(() => {
    if (selectedTopic && !sources.some((source) => source.topics.includes(selectedTopic))) {
      setSelectedTopic("");
    }
  }, [selectedTopic, sources]);
  return (
    <div className="table-section source-library-panel">
      <PanelHeader icon={<Database size={18} />} title="Saved Sources" count={library?.source_count} />
      {error && (
        <div className="source-library-error" role="status">
          <strong>Source library unavailable</strong>
          <span>{error}</span>
        </div>
      )}
      {library && (
        <div className="source-library-summary" aria-label="Saved source summary">
          <span>
            <strong>{library.enabled_count}</strong>
            active
          </span>
          <span>
            <strong>{library.source_count - library.enabled_count}</strong>
            paused
          </span>
          <div className="source-library-topics" aria-label="Filter saved sources by topic" title={library.topics.join(", ")}>
            {topicPreview.length ? (
              <>
                {topicPreview.map((topic) => (
                  <button
                    aria-pressed={selectedTopic === topic}
                    key={topic}
                    onClick={() => setSelectedTopic(selectedTopic === topic ? "" : topic)}
                    type="button"
                  >
                    {topic}
                  </button>
                ))}
                {hiddenTopicCount > 0 && <small>+{hiddenTopicCount}</small>}
              </>
            ) : (
              <small>No topics yet</small>
            )}
          </div>
        </div>
      )}
      {sources.length > 0 && (
        <label className="source-library-search">
          <span>Find source</span>
          <input
            onChange={(event) => setQuery(event.target.value)}
            placeholder="@remote_jobs or jobs"
            type="search"
            value={query}
          />
          <small aria-live="polite">
            {filteredSources.length} of {sources.length} shown
          </small>
        </label>
      )}
      {isLoading ? (
        <InlineEmpty title="Loading saved sources" />
      ) : sources.length ? (
        <div className="source-library-list">
          {filteredSources.map((source) => (
            <SourceLibraryRow
              busy={busy}
              key={source.source_id}
              setSourceEnabled={setSourceEnabled}
              setSourceTopics={setSourceTopics}
              source={source}
            />
          ))}
          {!filteredSources.length && <InlineEmpty title="No saved source matches" />}
        </div>
      ) : (
        !error && <InlineEmpty title="No saved sources yet" />
      )}
    </div>
  );
}

export function filterDeskSourcesByQuery(sources: DeskSource[], query: string, selectedTopic = "") {
  const normalizedQuery = query.trim().toLowerCase();
  const normalizedTopic = selectedTopic.trim().toLowerCase();
  if (!normalizedQuery && !normalizedTopic) {
    return sources;
  }
  return sources.filter((source) => {
    const matchesTopic = normalizedTopic
      ? source.topics.some((topic) => topic.trim().toLowerCase() === normalizedTopic)
      : true;
    if (!matchesTopic) {
      return false;
    }
    if (!normalizedQuery) {
      return true;
    }
    return [source.label, source.channel, source.priority, ...source.topics]
      .join(" ")
      .toLowerCase()
      .includes(normalizedQuery);
  });
}

function SourceLibraryRow({
  source,
  busy,
  setSourceEnabled,
  setSourceTopics,
}: {
  source: DeskSource;
  busy: boolean;
  setSourceEnabled: (sourceId: string, enabled: boolean) => Promise<void>;
  setSourceTopics: (sourceId: string, topics: string[]) => Promise<void>;
}) {
  const [editingTopics, setEditingTopics] = useState(false);
  const [topicText, setTopicText] = useState(source.topics.join(", "));
  const [saveError, setSaveError] = useState("");
  const topicInputRef = useRef<HTMLInputElement | null>(null);
  const editorId = `source-topic-editor-${source.source_id.replace(/[^a-z0-9_-]/gi, "-")}`;
  const topicState = sourceTopicsEditState(source.topics, topicText);

  useEffect(() => {
    setTopicText(source.topics.join(", "));
    setEditingTopics(false);
    setSaveError("");
  }, [source.source_id, source.topics]);

  useEffect(() => {
    if (editingTopics) {
      topicInputRef.current?.focus();
    }
  }, [editingTopics]);

  return (
    <article className={`source-library-row ${source.enabled ? "enabled" : "paused"}`}>
      <div className="source-library-main">
        <strong title={source.label}>{source.label}</strong>
        <small title={`@${source.channel}`}>@{source.channel}</small>
        <div className="source-library-tags" aria-label={`${source.label} topics`}>
          {source.topics.map((topic) => (
            <span key={topic} title={`Topic: ${topic}`}>
              {topic}
            </span>
          ))}
          <span title="Recent messages scanned for this source">{source.scan_window_hours}h window</span>
          <span title="Source priority">{source.priority}</span>
        </div>
        {editingTopics && (
          <form
            id={editorId}
            className="source-topic-editor"
            onKeyDown={(event) => {
              if (event.key === "Escape") {
                event.preventDefault();
                setTopicText(source.topics.join(", "));
                setSaveError("");
                setEditingTopics(false);
              }
            }}
            onSubmit={(event) => {
              event.preventDefault();
              if (!topicState.canSave) {
                return;
              }
              setSaveError("");
              void setSourceTopics(source.source_id, topicState.topics)
                .then(() => setEditingTopics(false))
                .catch((error: unknown) => {
                  setSaveError(error instanceof Error ? error.message : "Could not save topics.");
                });
            }}
          >
            <label>
              <span>Topics</span>
              <input
                maxLength={200}
                onChange={(event) => {
                  setTopicText(event.target.value);
                  setSaveError("");
                }}
                placeholder="jobs, remote-work"
                ref={topicInputRef}
                type="text"
                value={topicText}
              />
            </label>
            <small aria-live="polite">{saveError || topicState.message}</small>
            <div className="source-topic-actions">
              <button className="text-button" disabled={busy || !topicState.canSave} type="submit">
                <Save size={15} />
                <span>Save topics</span>
              </button>
              <button
                className="text-button secondary"
                disabled={busy}
                onClick={() => {
                  setTopicText(source.topics.join(", "));
                  setSaveError("");
                  setEditingTopics(false);
                }}
                type="button"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </div>
      <div className="source-library-side">
        <span className={source.enabled ? "status enabled" : "status disabled"}>
          {source.enabled ? "Active" : "Paused"}
        </span>
        <button
          aria-label={`${source.label}: ${source.enabled ? "Pause" : "Use"}`}
          className={`text-button ${source.enabled ? "secondary" : ""}`}
          disabled={busy}
          onClick={() => void setSourceEnabled(source.source_id, !source.enabled)}
          type="button"
        >
          {source.enabled ? <Pause size={15} /> : <Play size={15} />}
          <span>{source.enabled ? "Pause" : "Use"}</span>
        </button>
        <button
          aria-controls={editorId}
          aria-expanded={editingTopics}
          aria-label={`${source.label}: ${editingTopics ? "Hide topic editor" : "Edit topics"}`}
          className="text-button secondary"
          disabled={busy}
          onClick={() => {
            setSaveError("");
            setEditingTopics((current) => !current);
          }}
          type="button"
        >
          <span>{editingTopics ? "Hide editor" : "Edit topics"}</span>
        </button>
      </div>
    </article>
  );
}

export function sourceTopicsEditState(currentTopics: string[], text: string) {
  const rawTopics = text
    .split(/[,\n]/)
    .map((topic) => topic.trim().toLowerCase())
    .filter(Boolean);
  const topics = Array.from(new Set(rawTopics));
  const invalid = topics.find((topic) => !/^[a-z0-9][a-z0-9_-]{1,40}$/.test(topic));
  const normalizedCurrent = currentTopics.map((topic) => topic.trim().toLowerCase()).filter(Boolean);
  const unchanged = topics.join("\0") === normalizedCurrent.join("\0");
  if (invalid) {
    return { canSave: false, topics, message: "Use short tags like jobs or remote-work." };
  }
  if (!topics.length) {
    return { canSave: false, topics, message: "Add at least one topic tag." };
  }
  if (topics.length > 8) {
    return { canSave: false, topics, message: "Use fewer topic tags." };
  }
  if (unchanged) {
    return { canSave: false, topics, message: "Topics are unchanged." };
  }
  return { canSave: true, topics, message: "Comma-separated tags. These tags only organize your sources." };
}

function SourceImportPanel({
  result,
  previewSourceImport,
  importSources,
  busy,
}: {
  result: SourceImportResult | null;
  previewSourceImport: (sources: string, topic: string) => Promise<SourceImportResult>;
  importSources: (sources: string, topic: string) => Promise<SourceImportResult>;
  busy: boolean;
}) {
  const [sources, setSources] = useState("");
  const [topic, setTopic] = useState("jobs");
  const [previewKey, setPreviewKey] = useState("");
  const currentKey = `${sources.trim()}\n${topic.trim().toLowerCase() || "jobs"}`;
  const canPreview = sources.trim().length > 0;
  const canImport = canPreview && previewKey === currentKey && result?.dry_run === true;
  const previewSources = result?.preview_sources ?? [];
  return (
    <form
      className="table-section source-import-panel"
      onSubmit={(event) => {
        event.preventDefault();
        if (!canPreview) {
          return;
        }
        void previewSourceImport(sources, topic)
          .then((next) => {
            if (next.dry_run) {
              setPreviewKey(currentKey);
            }
          })
          .catch(() => undefined);
      }}
    >
      <PanelHeader icon={<Upload size={18} />} title="Add Sources" />
      <label className="source-import-field">
        <span>Telegram channels</span>
        <textarea
          onChange={(event) => setSources(event.target.value)}
          placeholder={"@remote_jobs\nhttps://t.me/s/miniapps_jobs"}
          rows={5}
          value={sources}
        />
      </label>
      <label className="source-import-topic">
        <span>Topic</span>
        <input onChange={(event) => setTopic(event.target.value)} type="text" value={topic} />
      </label>
      <p className="delivery-note">Paste channel handles or t.me links, one per line. Preview checks duplicates before anything is saved.</p>
      <div className="source-import-actions">
        <button className="text-button secondary" disabled={busy || !canPreview} type="submit">
          <Eye size={15} />
          <span>{busy ? "Checking" : "Preview sources"}</span>
        </button>
        <button
          className="text-button"
          disabled={busy || !canImport}
          onClick={() => void importSources(sources, topic).catch(() => undefined)}
          type="button"
        >
          <Upload size={15} />
          <span>Import sources</span>
        </button>
      </div>
      {canPreview && !canImport && result?.dry_run && <span className="delivery-dirty">Preview again before importing</span>}
      {result && (
        <div className={`source-import-result ${result.written ? "written" : "preview"}`} role="status">
          <strong>{result.title || (result.written ? "Sources saved" : "Source preview ready")}</strong>
          <span>
            {result.added_count} new / {result.updated_count} updated / {result.unchanged_count} already saved
          </span>
          {previewSources.length > 0 && (
            <div className="source-import-preview-list" aria-label="Preview sources">
              {previewSources.map((source) => (
                <small key={source.source_id}>{source.label}</small>
              ))}
              {result.preview_truncated_count > 0 && <small>+{result.preview_truncated_count} more</small>}
            </div>
          )}
          {result.next_action && <em>{result.next_action}</em>}
        </div>
      )}
    </form>
  );
}

function deliveryChatId(target: DeliveryTarget) {
  return typeof target.config.chat_id === "string" ? target.config.chat_id : "";
}

function DeliveryTargetEditor({
  target,
  testResult,
  saveDeliveryTarget,
  testDeliveryTarget,
  busy,
}: {
  target: DeliveryTarget;
  testResult: DeliveryTestResult | null;
  saveDeliveryTarget: (targetId: string, chatId: string, enabled: boolean) => Promise<void>;
  testDeliveryTarget: (targetId: string, chatId: string) => Promise<void>;
  busy: boolean;
}) {
  const [chatId, setChatId] = useState(deliveryChatId(target));
  const [enabled, setEnabled] = useState(target.enabled);

  useEffect(() => {
    setChatId(deliveryChatId(target));
    setEnabled(target.enabled);
  }, [target]);

  const canEnable = !enabled || chatId.trim().length > 0;
  const hasUnsavedChanges = chatId !== deliveryChatId(target) || enabled !== target.enabled;
  return (
    <form
      className="delivery-target-editor"
      onSubmit={(event) => {
        event.preventDefault();
        if (!canEnable) {
          return;
        }
        void saveDeliveryTarget(target.target_id, chatId, enabled);
      }}
    >
      <div className="delivery-target-head">
        <div>
          <strong title={target.display_name || deliveryTargetName(target)}>
            {target.display_name || deliveryTargetName(target)}
          </strong>
          <small>{target.detail || deliveryTargetDetail(target)}</small>
        </div>
        <span className={target.enabled ? "status enabled" : "status disabled"}>
          {target.status_label || (target.enabled ? "Live" : "Muted")}
        </span>
      </div>
      <label className="delivery-field">
        <span>Telegram chat ID</span>
        <input
          autoComplete="off"
          onChange={(event) => setChatId(event.target.value)}
          placeholder="@channel or -1001234567890"
          type="text"
          value={chatId}
        />
      </label>
      <label className="delivery-toggle">
        <input checked={enabled} onChange={(event) => setEnabled(event.target.checked)} type="checkbox" />
        <span>Allow live notifications</span>
      </label>
      <p className="delivery-note">Paste a Telegram channel handle or the numeric chat ID you want alerts to use.</p>
      <div className="delivery-actions">
        <button className="text-button" disabled={busy || !canEnable} type="submit">
          <Save size={15} />
          <span>{busy ? "Saving" : hasUnsavedChanges ? "Save changes" : "Save settings"}</span>
        </button>
        <button
          className="text-button secondary"
          disabled={busy}
          onClick={() => void testDeliveryTarget(target.target_id, chatId)}
          type="button"
        >
          <CircleDashed size={15} />
          <span>Test without sending</span>
        </button>
      </div>
      <p className="delivery-note">The dry run checks the saved target without sending a Telegram message.</p>
      {hasUnsavedChanges && <span className="delivery-dirty">Unsaved changes</span>}
      {testResult && (
        <div className={`delivery-test-result ${testResult.ok ? "ok" : "failed"}`} role="status">
          <strong>{testResult.title || "Notification test"}</strong>
          <span>{testResult.detail || testResult.status}</span>
        </div>
      )}
    </form>
  );
}

function SourceYieldMap({ sources }: { sources: SourceStat[] }) {
  const visibleSources = sources.slice(0, SOURCE_CARD_LIMIT);
  const heatSources = sources.slice(0, SOURCE_HEAT_LIMIT);
  const activeCount = sources.filter((source) => (source.card_count ?? 0) > 0 || (source.latest_card_count ?? 0) > 0).length;
  const hotCount = sources.filter((source) => (source.high_count ?? 0) > 0).length;
  const riskCount = sources.filter((source) => source.scan_failure || source.scan_incomplete).length;
  return (
    <div className="source-yield-map" aria-label="Source yield map">
      <div className="source-heat-panel" aria-label="Source signal heat map">
        <div className="source-heat-grid">
          {heatSources.map((source) => (
            <span
              className={`source-heat-cell ${sourceHeatClass(source)}`}
              key={source.channel}
              title={`${source.display_name || channelDisplayName(source.channel)} · ${source.high_count} high · ${source.card_count} cards`}
              style={{ "--heat": percentWidth(sourceSignalScore(source)) } as CSSProperties}
            />
          ))}
        </div>
        <div className="source-heat-legend">
          <strong>{sources.length}</strong>
          <span>sources</span>
          <small>
            {hotCount} hot / {activeCount} active{riskCount ? ` / ${riskCount} risk` : ""}
          </small>
        </div>
      </div>
      {visibleSources.map((source) => (
        <article
          className={`source-yield-card ${source.scan_failure ? "risk" : ""} ${source.high_count ? "" : "zero"}`}
          key={source.channel}
        >
          <div className="source-yield-head">
            <SourceChannelCell source={source} />
            <span className="source-yield-score" title={`${source.high_count} high-signal cards`}>
              <strong>{source.high_count}</strong>
              <small>high</small>
            </span>
          </div>
          <div className="source-bars">
            <MetricBar
              label="Latest kept"
              value={source.scan_keep_rate ?? 0}
              detail={`${source.kept_count ?? 0}/${source.raw_count ?? 0}`}
            />
            <MetricBar label="Card yield" value={source.card_yield_rate ?? 0} detail={formatPercent(source.card_yield_rate ?? 0)} />
          </div>
          <div className="source-mini-stats">
            <SourceMiniStats
              emptyLabel="quiet"
              items={[
                { label: "cards", value: source.latest_card_count ?? source.card_count },
                { label: "alerts", value: source.alert_count },
                { label: "false", value: source.false_positive_count },
              ]}
            />
          </div>
        </article>
      ))}
    </div>
  );
}

function MetricBar({ label, value, detail }: { label: string; value: number; detail: string }) {
  return (
    <div className="metric-line" aria-label={`${label}: ${detail}`} title={`${label}: ${detail}`}>
      <span className="metric-label">{metricShortLabel(label)}</span>
      <div className={`metric-bar ${value <= 0 ? "empty" : ""}`}>
        <span style={{ width: percentWidth(value) }} />
      </div>
      <span className="metric-detail">{detail}</span>
    </div>
  );
}

function FeedbackFlow({ summary }: { summary?: DashboardState["feedback_summary"] }) {
  return (
    <div className="feedback-flow" aria-label="Feedback learning flow">
      <span title="Ready for note-free feedback export">
        <strong>{summary?.exportable_count ?? 0}</strong>
        export
      </span>
      <span title="Profile changes waiting for review">
        <strong>{summary?.pending_profile_diff_count ?? 0}</strong>
        pending
      </span>
      <span title="Applied profile changes">
        <strong>{summary?.applied_profile_diff_count ?? 0}</strong>
        applied
      </span>
    </div>
  );
}

function FeedbackBreakdown({
  summary,
  exportableCount,
}: {
  summary?: DashboardState["feedback_summary"];
  exportableCount: number;
}) {
  const items = [
    { label: "Keep", value: summary?.by_action?.keep ?? 0 },
    { label: "Skip", value: summary?.by_action?.skip ?? 0 },
    { label: "False", value: summary?.by_action?.false_positive ?? 0 },
    { label: "Diff", value: summary?.non_exportable_follow_up_count ?? 0 },
    { label: "High", value: summary?.by_rating?.high ?? 0 },
    { label: "Changed", value: summary?.by_decision_status?.changed ?? 0 },
  ].filter((item) => item.value > 0);
  if (!items.length) {
    return (
      <InlineEmpty
        title={exportableCount > 0 ? "Feedback rows need action labels" : "No feedback actions yet"}
      />
    );
  }
  return (
    <div className="feedback-breakdown" aria-label="Feedback action counts">
      {items.map((item) => (
        <span className={item.value > 0 ? "" : "muted"} key={item.label}>
          {item.label} {item.value}
        </span>
      ))}
    </div>
  );
}

function SourceActionGrid({ insights }: { insights: SourceInsight[] }) {
  const visible = insights.slice(0, SOURCE_ACTION_LIMIT);
  const hiddenCount = Math.max(0, insights.length - visible.length);
  return (
    <div className="insight-list">
      {visible.map((insight, index) => (
        <article className={`source-insight ${insight.kind}`} key={`${insight.kind}-${insight.channel}-${index}`}>
          <div className="source-insight-head">
            <span className={`status ${insight.kind}`}>{insight.label}</span>
            <small>{insight.confidence || "medium"}</small>
          </div>
          <strong title={`@${insight.channel}`}>{insight.display_name || channelDisplayName(insight.channel)}</strong>
          <div className="source-insight-bars">
            <MetricBar
              label="Latest kept"
              value={insight.stats.scan_keep_rate ?? 0}
              detail={`${insight.stats.kept_count ?? 0}/${insight.stats.raw_count ?? 0}`}
            />
            <MetricBar
              label="High-rate"
              value={insight.stats.high_rate ?? 0}
              detail={formatPercent(insight.stats.high_rate ?? 0)}
            />
          </div>
          <div
            className="source-next-action"
            title={insight.next_action?.detail || insight.reason}
            aria-label={`${insight.next_action?.label || "Review source"}: ${insight.next_action?.detail || insight.reason}`}
          >
            <span>{insight.next_action?.label || "Review source"}</span>
          </div>
          <div className="source-mini-stats">
            <SourceMiniStats
              emptyLabel="no noise"
              items={[
                { label: "high", value: insight.stats.high_count },
                { label: "cards", value: insight.stats.latest_card_count ?? insight.stats.card_count },
                { label: "false", value: insight.stats.false_positive_count },
              ]}
            />
          </div>
        </article>
      ))}
      {hiddenCount > 0 && <div className="list-overflow-note">+{hiddenCount} more source actions queued</div>}
    </div>
  );
}

function FeedbackNextAction({ action }: { action: DashboardNextAction }) {
  return (
    <div className="feedback-next-action" aria-label="Feedback next action">
      <span className="panel-kicker">Learning loop</span>
      <strong>{action.label || "Collect feedback"}</strong>
      {action.detail && <small>{action.detail}</small>}
    </div>
  );
}

function FeedbackImpactList({ impacts }: { impacts: FeedbackImpact[] }) {
  const visible = impacts.slice(0, FEEDBACK_IMPACT_LIMIT);
  const hiddenCount = Math.max(0, impacts.length - visible.length);
  if (!visible.length) {
    return <InlineEmpty title="No feedback impact yet" />;
  }
  return (
    <div className="feedback-impact-list" aria-label="Recent feedback impact">
      {visible.map((impact, index) => (
        <article className={`feedback-impact ${toneClass(impact.impact_status || "unknown")}`} key={feedbackImpactKey(impact, index)}>
          <span>{impact.impact_label || "Feedback recorded"}</span>
          <strong>{impact.item_title || "Review card"}</strong>
          <small>
            {formatActionLabel(impact.action || "feedback")} / {impact.rating || "unknown"} /{" "}
            {impact.decision_status || "unknown"}
          </small>
        </article>
      ))}
      {hiddenCount > 0 && <div className="list-overflow-note">+{hiddenCount} more feedback impacts saved</div>}
    </div>
  );
}

function SourceMiniStats({
  items,
  emptyLabel,
}: {
  items: Array<{ label: string; value?: number | null }>;
  emptyLabel: string;
}) {
  const visible = items.filter((item) => (item.value ?? 0) > 0);
  if (!visible.length) {
    return <span className="muted">{emptyLabel}</span>;
  }
  return (
    <>
      {visible.map((item) => (
        <span key={item.label}>
          {item.value} {item.label}
        </span>
      ))}
    </>
  );
}

function SourceChannelCell({ source }: { source: SourceStat }) {
  return (
    <div className="source-channel-cell">
      <strong title={`@${source.channel}`}>{source.display_name || channelDisplayName(source.channel)}</strong>
      {(source.scan_failure || source.scan_incomplete) && (
        <span className={source.scan_failure ? "source-risk-badge failure" : "source-risk-badge incomplete"}>
          {source.scan_failure ? "Access" : "Incomplete"}
        </span>
      )}
    </div>
  );
}
