import { useState } from "react";
import { Database, Eye, Save, Upload } from "lucide-react";

import type { SourceImportResult } from "../../domain/types";

export function SourceImportPanel({
  result,
  previewSourceImport,
  importSources,
  importStarterSources,
  previewSourceAssistant,
  applySourceAssistant,
  busy,
  hasSavedSources,
}: {
  result: SourceImportResult | null;
  previewSourceImport: (sources: string, topic: string) => Promise<SourceImportResult>;
  importSources: (sources: string, topic: string) => Promise<SourceImportResult>;
  importStarterSources: (topic: string) => Promise<SourceImportResult>;
  previewSourceAssistant: (instruction: string, topic: string, confirmExternalAi?: boolean) => Promise<SourceImportResult>;
  applySourceAssistant: (
    instruction: string,
    topic: string,
    confirmExternalAi?: boolean,
    resolvedPlan?: SourceImportResult["resolved_plan"],
  ) => Promise<SourceImportResult>;
  busy: boolean;
  hasSavedSources: boolean;
}) {
  const [sources, setSources] = useState("");
  const [topic, setTopic] = useState("jobs");
  const [assistantText, setAssistantText] = useState("");
  const [assistantExternalAi, setAssistantExternalAi] = useState(false);
  const [assistantPreviewKey, setAssistantPreviewKey] = useState("");
  const [previewKey, setPreviewKey] = useState("");
  const currentKey = `${sources.trim()}\n${topic.trim().toLowerCase() || "jobs"}`;
  const assistantKey = `${assistantText.trim()}\n${topic.trim().toLowerCase() || "jobs"}\n${assistantExternalAi ? "ai" : "local"}`;
  const assistantOperationCount = result
    ? result.added_count + result.updated_count + (result.removed_count ?? 0) + (result.enabled_count ?? 0) + (result.disabled_count ?? 0)
    : 0;
  const canPreview = sources.trim().length > 0;
  const canImport = canPreview && previewKey === currentKey && result?.dry_run === true;
  const canAssistantPreview = assistantText.trim().length > 0;
  const canAssistantApply =
    canAssistantPreview &&
    assistantPreviewKey === assistantKey &&
    result?.dry_run === true &&
    result.action === "assistant" &&
    assistantOperationCount > 0 &&
    !!result.resolved_plan;
  const previewSources = result?.preview_sources ?? [];
  return (
    <details className="table-section source-import-panel source-import-details" open={!hasSavedSources}>
      <summary>
        <span className="panel-title">
          <Upload size={18} />
          Add Sources
        </span>
        {hasSavedSources && <small>Open when adding new channels</small>}
      </summary>
      <div className="source-quick-actions" aria-label="One-click source setup">
        <button
          className="text-button"
          disabled={busy}
          onClick={() => void importStarterSources(topic).catch(() => undefined)}
          type="button"
        >
          <Database size={15} />
          <span>Use starter set</span>
        </button>
      </div>
      <form
        className="source-import-form source-assistant-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (!canAssistantPreview) {
            return;
          }
          void previewSourceAssistant(assistantText, topic, assistantExternalAi)
            .then((next) => {
              if (next.dry_run && next.action === "assistant") {
                setAssistantPreviewKey(assistantKey);
              }
            })
            .catch(() => undefined);
        }}
      >
        <label className="source-import-field">
          <span>Source assistant</span>
          <textarea
            onChange={(event) => {
              setAssistantText(event.target.value);
              setAssistantPreviewKey("");
            }}
            placeholder={"add @remote_jobs and @frontend_jobs\npause @old_jobs\nremove @spam_jobs"}
            rows={4}
            value={assistantText}
          />
        </label>
        <div className="source-import-actions">
          <label className="source-assistant-ai">
            <input
              checked={assistantExternalAi}
              onChange={(event) => {
                setAssistantExternalAi(event.target.checked);
                setAssistantPreviewKey("");
              }}
              type="checkbox"
            />
            <span>Use AI on saved source names</span>
          </label>
          <button className="text-button secondary" disabled={busy || !canAssistantPreview} type="submit">
            <Eye size={15} />
            <span>{busy ? "Checking" : "Preview plan"}</span>
          </button>
          <button
            className="text-button"
            disabled={busy || !canAssistantApply}
            onClick={() => void applySourceAssistant(assistantText, topic, assistantExternalAi, result?.resolved_plan).catch(() => undefined)}
            type="button"
          >
            <Save size={15} />
            <span>Apply plan</span>
          </button>
        </div>
      </form>
      <form
        className="source-import-form"
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
              {result.removed_count ? ` / ${result.removed_count} removed` : ""}
              {result.enabled_count ? ` / ${result.enabled_count} enabled` : ""}
              {result.disabled_count ? ` / ${result.disabled_count} paused` : ""}
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
    </details>
  );
}
