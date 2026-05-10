import { Copy, Download, Play, RotateCcw, Trash2 } from "lucide-react";

import { InlineEmpty, PanelHeader } from "../common";
import { feedbackImpactKey, formatActionLabel, toneClass } from "../../domain/display";
import type { DashboardNextAction, DashboardState, FeedbackExportResult, FeedbackImpact } from "../../domain/types";

const FEEDBACK_IMPACT_LIMIT = 4;

export function learningActionLabel(count: number) {
  return count > 0 ? "Apply feedback to future reports" : "Collect review decisions";
}

export function feedbackExportStatusLine(result: FeedbackExportResult | null) {
  if (!result) {
    return "";
  }
  const decisionLabel = result.feedback_count === 1 ? "decision" : "decisions";
  return `${result.feedback_count} ${decisionLabel} applied to future reports · ${result.output_path}`;
}

export function LearningPanel({
  summary,
  exportResult,
  exportFeedback,
  clearFeedback,
  undoFeedbackDecision,
  runAgainWithLearning,
  busy,
}: {
  summary?: DashboardState["feedback_summary"];
  exportResult: FeedbackExportResult | null;
  exportFeedback: () => void;
  clearFeedback: () => void;
  undoFeedbackDecision: (cardId: string) => void;
  runAgainWithLearning: () => void;
  busy: boolean;
}) {
  const exportableCount = summary?.exportable_count ?? exportResult?.feedback_count ?? 0;
  const currentDecisionCount = summary?.current_decision_count ?? exportableCount + (summary?.non_exportable_follow_up_count ?? 0);
  const statusLine = feedbackExportStatusLine(exportResult);
  const copyExportPath = () => {
    if (!exportResult?.output_path || !navigator.clipboard) {
      return;
    }
    void navigator.clipboard.writeText(exportResult.output_path);
  };

  return (
    <div className="table-section feedback-export-panel learning-panel">
      <PanelHeader icon={<Download size={18} />} title="Learning" count={currentDecisionCount} />
      <FeedbackBreakdown summary={summary} exportableCount={exportableCount} />
      {summary?.next_action && <FeedbackNextAction action={summary.next_action} />}
      <FeedbackFlow summary={summary} />
      <FeedbackImpactList impacts={summary?.recent_impacts ?? []} undoFeedbackDecision={undoFeedbackDecision} busy={busy} />
      <div className="feedback-export-row">
        <button className="text-button" type="button" onClick={exportFeedback} disabled={busy || exportableCount <= 0}>
          <Download size={15} />
          <span>{busy ? "Applying" : learningActionLabel(exportableCount)}</span>
        </button>
        <button className="text-button secondary" type="button" onClick={clearFeedback} disabled={busy}>
          <Trash2 size={15} />
          <span>Clear learning decisions</span>
        </button>
      </div>
      {statusLine && (
        <div className="feedback-export-result" aria-label="Latest learning export">
          <span className="artifact-chip" title={exportResult?.output_path}>
            {statusLine}
          </span>
          <div className="feedback-export-row compact">
            <button className="text-button secondary" type="button" onClick={copyExportPath}>
              <Copy size={15} />
              <span>Copy path</span>
            </button>
            <button className="text-button secondary" type="button" onClick={runAgainWithLearning} disabled={busy}>
              <Play size={15} />
              <span>Run again with learning</span>
            </button>
          </div>
        </div>
      )}
      <details className="settings-evidence feedback-troubleshooting">
        <summary>
          <Download size={16} />
          <span>Troubleshooting details</span>
        </summary>
        <div className="feedback-export-result">
          <span className="panel-kicker">Export JSONL</span>
          <small>{exportResult?.output_path || summary?.last_export_path || "output/feedback/review-feedback.jsonl"}</small>
        </div>
      </details>
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
      <span title="Preference drafts waiting for review">
        <strong>{summary?.pending_profile_diff_count ?? 0}</strong>
        pending
      </span>
      <span title="Applied preference drafts">
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
    { label: "Draft", value: summary?.non_exportable_follow_up_count ?? 0 },
    { label: "High", value: summary?.by_rating?.high ?? 0 },
    { label: "Changed", value: summary?.by_decision_status?.changed ?? 0 },
  ].filter((item) => item.value > 0);
  if (!items.length) {
    return <InlineEmpty title={exportableCount > 0 ? "Feedback rows need action labels" : "No learning decisions yet"} />;
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

function FeedbackNextAction({ action }: { action: DashboardNextAction }) {
  return (
    <div className="feedback-next-action" aria-label="Feedback next action">
      <span className="panel-kicker">Learning loop</span>
      <strong>{action.label || "Collect feedback"}</strong>
      {action.detail && <small>{action.detail}</small>}
    </div>
  );
}

function FeedbackImpactList({
  impacts,
  undoFeedbackDecision,
  busy,
}: {
  impacts: FeedbackImpact[];
  undoFeedbackDecision: (cardId: string) => void;
  busy: boolean;
}) {
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
          {impact.card_id && (
            <button className="icon-button" type="button" onClick={() => undoFeedbackDecision(impact.card_id || "")} disabled={busy} title="Undo decision">
              <RotateCcw size={14} />
            </button>
          )}
        </article>
      ))}
      {hiddenCount > 0 && <div className="list-overflow-note">+{hiddenCount} more feedback impacts saved</div>}
    </div>
  );
}
