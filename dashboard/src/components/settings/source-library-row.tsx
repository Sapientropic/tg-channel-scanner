import { useEffect, useRef, useState } from "react";
import { CirclePause, CirclePlay, Save, Trash2 } from "lucide-react";

import type { DeskSource } from "../../domain/types";
import { sourceTopicsEditState } from "./source-library-model";

export function SourceLibraryRow({
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

  // Keep this row as a stable top-level component. The topic editor should not
  // lose typed text or an async save error when the parent panel rerenders for
  // search, topic-chip, or pagination state changes.
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
