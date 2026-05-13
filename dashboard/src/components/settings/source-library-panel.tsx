import { useEffect, useRef, useState } from "react";
import { CirclePause, CirclePlay, Database, Save, Trash2 } from "lucide-react";

import { InlineEmpty } from "../common";
import type { DeskSource, DeskSourcesResult, SourceStat } from "../../domain/types";

export const SOURCE_LIBRARY_PAGE_SIZE = 8;

export function SourceLibraryPanel({
  library,
  error,
  busy,
  removeSource,
  setSourceEnabled,
  setSourceTopics,
  sourceStats,
}: {
  library: DeskSourcesResult | null;
  error: string | null;
  busy: boolean;
  removeSource: (sourceId: string) => Promise<void>;
  setSourceEnabled: (sourceId: string, enabled: boolean) => Promise<void>;
  setSourceTopics: (sourceId: string, topics: string[]) => Promise<void>;
  sourceStats: SourceStat[];
}) {
  const sources = library?.sources ?? [];
  const isLoading = !library && !error;
  const [query, setQuery] = useState("");
  const [selectedTopic, setSelectedTopic] = useState("");
  const [showAllTopics, setShowAllTopics] = useState(false);
  const [showSourceList, setShowSourceList] = useState(false);
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [visibleCount, setVisibleCount] = useState(SOURCE_LIBRARY_PAGE_SIZE);
  const filteredSources = filterDeskSourcesByQuery(sources, query, selectedTopic);
  const visibleSources = paginatedDeskSources(filteredSources, visibleCount);
  const hiddenSourceCount = Math.max(0, filteredSources.length - visibleSources.length);
  const topics = library?.topics ?? [];
  const topicPreview = showAllTopics ? topics : topics.slice(0, 12);
  const hiddenTopicCount = Math.max(0, topics.length - topicPreview.length);
  const hasFilters = Boolean(query.trim() || selectedTopic);
  const listVisible = showSourceList || hasFilters;
  const managementOpen = libraryOpen || hasFilters || showSourceList || isLoading || Boolean(error) || !sources.length;
  const activityLabel = sourceLibraryActivityLabel(sourceStats);
  const countLabel = listVisible
    ? sourceLibraryCountLabel(visibleSources.length, filteredSources.length, hasFilters)
    : `${filteredSources.length} saved; search or manage when needed`;
  useEffect(() => {
    if (selectedTopic && !sources.some((source) => source.topics.includes(selectedTopic))) {
      setSelectedTopic("");
    }
  }, [selectedTopic, sources]);
  useEffect(() => {
    setVisibleCount(SOURCE_LIBRARY_PAGE_SIZE);
  }, [query, selectedTopic, library?.source_count]);
  return (
    <div className="table-section source-library-panel">
      <details
        className="source-library-details"
        onToggle={(event) => setLibraryOpen(event.currentTarget.open)}
        open={managementOpen}
      >
        <summary>
          <span className="panel-title">
            <Database size={18} />
            Saved Sources
          </span>
          <strong>{library?.source_count ?? sources.length}</strong>
          <small>{sources.length ? activityLabel || "Open to search or manage" : "No saved sources yet"}</small>
        </summary>
        {error && (
          <div className="source-library-error" role="status">
            <strong>Saved sources need a refresh</strong>
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
                  {(hiddenTopicCount > 0 || showAllTopics) && (
                    <button
                      aria-expanded={showAllTopics}
                      className="topic-overflow-toggle"
                      onClick={() => setShowAllTopics((current) => !current)}
                      type="button"
                    >
                      {showAllTopics ? "Show fewer" : `+${hiddenTopicCount}`}
                    </button>
                  )}
                </>
              ) : (
                <small>No topics yet</small>
              )}
            </div>
          </div>
        )}
        {sources.length > 0 && (
          <div className="source-library-search">
            <label htmlFor="source-library-query">Find source</label>
            <input
              id="source-library-query"
              onChange={(event) => setQuery(event.target.value)}
              placeholder="@remote_jobs or jobs"
              type="search"
              value={query}
            />
            <small aria-live="polite">
              {countLabel}
            </small>
            {hasFilters && (
              <button
                className="text-button secondary source-library-clear"
                onClick={() => {
                  setQuery("");
                  setSelectedTopic("");
                }}
                type="button"
              >
                Clear filters
              </button>
            )}
          </div>
        )}
        {isLoading ? (
          <InlineEmpty title="Loading saved sources" />
        ) : sources.length && !listVisible ? (
          <div className="source-library-gate" aria-label="Saved source list collapsed">
            <div>
              <strong>{library?.source_count ?? sources.length} saved sources</strong>
              <span>Use search for one source, or open the list only when you need bulk cleanup.</span>
            </div>
            <button
              className="text-button secondary"
              onClick={() => setShowSourceList(true)}
              type="button"
            >
              Show first {SOURCE_LIBRARY_PAGE_SIZE}
            </button>
          </div>
        ) : sources.length ? (
          <div className="source-library-list">
            {visibleSources.map((source) => (
              <SourceLibraryRow
                busy={busy}
                key={source.source_id}
                removeSource={removeSource}
                setSourceEnabled={setSourceEnabled}
                setSourceTopics={setSourceTopics}
                source={source}
              />
            ))}
            {!filteredSources.length && <InlineEmpty title="No saved source matches" />}
            {hiddenSourceCount > 0 && (
              <button
                className="text-button secondary source-library-more"
                onClick={() => setVisibleCount((count) => count + SOURCE_LIBRARY_PAGE_SIZE)}
                type="button"
              >
                <span>Load 8 more</span>
                <small>{hiddenSourceCount} remaining</small>
              </button>
            )}
          </div>
        ) : (
          !error && <InlineEmpty title="No saved sources yet" />
        )}
      </details>
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

export function paginatedDeskSources(sources: DeskSource[], visibleCount = SOURCE_LIBRARY_PAGE_SIZE) {
  return sources.slice(0, Math.max(0, visibleCount));
}

export function sourceLibraryCountLabel(visibleCount: number, filteredCount: number, hasFilters: boolean) {
  const visible = Math.max(0, visibleCount);
  const filtered = Math.max(0, filteredCount);
  if (hasFilters) {
    if (!filtered) {
      return "No matching sources";
    }
    return visible >= filtered ? `${filtered} matching shown` : `${visible} of ${filtered} matching shown`;
  }
  if (!filtered) {
    return "No saved sources";
  }
  return visible >= filtered ? `Showing all ${filtered}` : `Showing first ${visible} of ${filtered}`;
}

export function sourceLibraryActivityLabel(sources: SourceStat[]) {
  if (!sources.length) {
    return "";
  }
  const latestCards = sources.reduce((sum, source) => sum + Math.max(0, source.latest_card_count ?? 0), 0);
  const alerts = sources.reduce((sum, source) => sum + Math.max(0, source.alert_count ?? 0), 0);
  const risk = sources.filter((source) => source.scan_failure || source.scan_incomplete).length;
  const parts = [
    latestCards ? `${latestCards} latest card${latestCards === 1 ? "" : "s"}` : "No latest cards",
    alerts ? `${alerts} alert${alerts === 1 ? "" : "s"}` : "",
    `${sources.length} tracked`,
    risk ? `${risk} risk` : "",
  ].filter(Boolean);
  return parts.join(" · ");
}

function SourceLibraryRow({
  source,
  busy,
  removeSource,
  setSourceEnabled,
  setSourceTopics,
}: {
  source: DeskSource;
  busy: boolean;
  removeSource: (sourceId: string) => Promise<void>;
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
      </div>
      <div className="source-library-tags" aria-label={`${source.label} topics`}>
        {source.topics.map((topic) => (
          <span key={topic} title={`Topic: ${topic}`}>
            {topic}
          </span>
        ))}
        <span title="Recent messages scanned for this source">{source.scan_window_hours}h window</span>
        <span title="Source priority">{source.priority}</span>
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
          {source.enabled ? <CirclePause size={15} /> : <CirclePlay size={15} />}
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
        <button
          aria-label={`${source.label}: Remove source`}
          className="text-button secondary danger"
          disabled={busy}
          onClick={() => void removeSource(source.source_id).catch(() => undefined)}
          type="button"
        >
          <Trash2 size={15} />
          <span>Remove</span>
        </button>
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
