import { type CSSProperties } from "react";

import { CopyableCommand, StatusLine } from "./common";
import {
  opportunityDetail,
  opportunityHeadline,
  opportunityTone,
  percentWidth,
  ratio,
} from "../domain/display";
import { profileDisplayName } from "../domain/format";
import { handledInboxCount, reviewQueueCount } from "../domain/inbox";
import type { DashboardState, Metric, OpportunitySummary, ValidationSummary } from "../domain/types";

export function OpportunitySummaryPanel({
  summary,
  latestPriorityCount,
}: {
  summary?: OpportunitySummary;
  latestPriorityCount?: number;
}) {
  if (!summary || summary.status === "no_runs") {
    return null;
  }
  const displaySummary = opportunityDisplaySummary(summary, latestPriorityCount);
  const tone = opportunityTone(displaySummary);
  const nextActionLabel = opportunityNextActionLabel(displaySummary.next_action?.label);
  return (
    <section className={`signal-brief ${tone}`} aria-label="Latest run opportunity summary">
      <div className="signal-brief-lede">
        <span className="panel-kicker">{displaySummary.display_name || profileDisplayName(displaySummary.profile_id || "profile")}</span>
        <strong>{opportunityHeadline(displaySummary)}</strong>
        <small>{opportunityDetail(displaySummary)}</small>
      </div>
      <OpportunityFunnel summary={displaySummary} />
      {displaySummary.next_action && (
        <div className="signal-next-action" aria-label="Recommended next action">
          <span className="panel-kicker">Next</span>
          <strong>{nextActionLabel || "Review run"}</strong>
          <DecisionMemoryLine counts={displaySummary.decision_counts} />
          {displaySummary.next_action.command && (
            <details className="signal-command">
              <summary>Advanced command</summary>
              <CopyableCommand command={displaySummary.next_action.command} label="next action" compact />
            </details>
          )}
        </div>
      )}
    </section>
  );
}

function opportunityDisplaySummary(summary: OpportunitySummary, latestPriorityCount?: number): OpportunitySummary {
  if (typeof latestPriorityCount !== "number" || hasBlockingOpportunitySummary(summary)) {
    return summary;
  }
  const originalCount = summary.high_actionable_count ?? 0;
  if (latestPriorityCount === originalCount) {
    return summary;
  }
  const nextAction =
    latestPriorityCount === 0 && isPriorityReviewAction(summary.next_action?.label) ? undefined : summary.next_action;
  return {
    ...summary,
    high_actionable_count: latestPriorityCount,
    all_clear: latestPriorityCount === 0 ? true : summary.all_clear,
    next_action: nextAction,
  };
}

function hasBlockingOpportunitySummary(summary: OpportunitySummary) {
  return (summary.diagnostics?.failure_count ?? 0) > 0 || summary.status === "failed";
}

function isPriorityReviewAction(label?: string) {
  const normalized = opportunityNextActionLabel(label);
  return normalized === "Review priority cards";
}

function OpportunityFunnel({ summary }: { summary: OpportunitySummary }) {
  const steps = [
    { label: "Scanned", value: summary.scanned_count ?? 0, tone: "teal" },
    { label: "Matched", value: summary.matched_count ?? 0, tone: "amber" },
    { label: "Cards", value: summary.review_card_count ?? 0, tone: "blue" },
    { label: "Priority", value: summary.high_actionable_count ?? 0, tone: "rust" },
  ];
  const maxValue = Math.max(1, ...steps.map((step) => step.value));
  return (
    <div className="signal-funnel" aria-label="Latest run funnel">
      {steps.map((step) => (
        <div className={`signal-funnel-step ${step.tone}`} key={step.label}>
          <span>{step.label}</span>
          <i aria-hidden="true">
            <b style={{ width: percentWidth(step.value / maxValue) }} />
          </i>
          <strong>{step.value}</strong>
        </div>
      ))}
    </div>
  );
}

function DecisionMemoryLine({ counts }: { counts?: Record<string, number> }) {
  if (!counts) {
    return null;
  }
  const entries = [
    ["New", counts.new ?? 0],
    ["Updated", counts.changed ?? 0],
    ["Seen", counts.seen ?? 0],
    ["Repeated", counts.recurring ?? 0],
  ].filter(([, value]) => Number(value) > 0);
  if (!entries.length) {
    return null;
  }
  return (
    <div className="signal-memory" aria-label="Decision memory counts">
      {entries.map(([label, value]) => (
        <span key={label}>
          {String(label)} {String(value)}
        </span>
      ))}
    </div>
  );
}

export function ValidationSummaryPanel({ summary }: { summary?: ValidationSummary }) {
  if (!summary) {
    return null;
  }
  const actions = Object.entries(summary.by_action ?? {}).filter(([, count]) => count > 0);
  const firstDecision = firstDecisionLabel(summary);
  const nextActionDetail = validationNextActionDetail(summary.next_action?.detail);
  return (
    <details className="validation-brief" aria-label="Local validation summary">
      <summary>
        <div className="validation-copy">
          <span className="panel-kicker">{summary.window_days ?? 14} day review window</span>
          <strong>{summary.next_action?.label || "Track real outcomes"}</strong>
          <small>{nextActionDetail || "Mark what happened so future matches improve."}</small>
        </div>
        <span className="validation-disclosure-label">Progress</span>
      </summary>
      <div className="validation-body">
        <div className="validation-stats">
          <StatusLine label="Scans" value={String(summary.runs_count ?? 0)} />
          <StatusLine label="High cards" value={String(summary.high_card_count ?? 0)} />
          <StatusLine label="Decisions" value={String(summary.action_count ?? 0)} />
          <StatusLine label="Waiting" value={String(summary.pending_count ?? 0)} />
          <StatusLine label="First action" value={firstDecision} />
        </div>
        <div className="validation-gauges" aria-label="Validation behavior rates">
          <ValidationGauge
            label="Reviewed"
            value={summary.triage_rate ?? ratio(summary.action_count, summary.card_count)}
            detail={`${summary.action_count ?? 0}/${summary.card_count ?? 0}`}
          />
          <ValidationGauge
            label="Keep rate"
            value={summary.keep_rate ?? 0}
            detail={`${Math.round((summary.keep_rate ?? 0) * 100)}%`}
          />
          {actions.length ? (
            actions.map(([action, count]) => (
              <span key={action}>
                {action.replace(/_/g, " ")} {count}
              </span>
            ))
          ) : (
            <span>No decisions yet</span>
          )}
        </div>
      </div>
    </details>
  );
}

function opportunityNextActionLabel(label?: string) {
  const normalized = String(label || "").trim();
  if (normalized === "Review action signals") {
    return "Review priority cards";
  }
  return normalized;
}

function validationNextActionDetail(detail?: string) {
  const normalized = String(detail || "").trim();
  if (normalized === "Mark keep, skip, false positive, or follow-up so the validation window has behavior evidence.") {
    return "Mark what happened so future matches improve.";
  }
  return normalized;
}

function firstDecisionLabel(summary: ValidationSummary) {
  if (typeof summary.first_decision_minutes !== "number") {
    return (summary.runs_count ?? 0) > 0 ? "Waiting" : "Not started";
  }
  const minutes = Math.max(0, Math.round(summary.first_decision_minutes));
  const timing = minutes < 1 ? "<1 min" : `${minutes} min`;
  const action = summary.first_decision_action?.trim().replace(/_/g, " ");
  return action ? `${timing} (${action})` : timing;
}

export function CommandStrip({ state, metrics }: { state: DashboardState; metrics: Metric[] }) {
  const queueCount = reviewQueueCount(state.inbox);
  const handledCount = handledInboxCount(state.inbox);
  const pulseWidth = queueCount ? Math.min(100, Math.max(8, queueCount * 18)) : 0;
  return (
    <section className="command-strip" aria-label="Dashboard status">
      <div className="pulse-panel">
        <span className="panel-kicker">Review queue</span>
        <strong>{queueCount}</strong>
        <small>{queueCount ? "cards to decide" : handledCount ? `${handledCount} handled` : "queue clear"}</small>
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

function MetricTile({ metric }: { metric: Metric }) {
  return (
    <article className={`metric-tile ${metric.tone}`} title={metric.detail}>
      <span>{metric.label}</span>
      <strong>{metric.value}</strong>
      {typeof metric.meter === "number" && (
        <div className="metric-tile-meter" style={{ "--meter": percentWidth(metric.meter) } as CSSProperties} aria-hidden="true">
          <i />
        </div>
      )}
    </article>
  );
}

function ValidationGauge({ label, value, detail }: { label: string; value: number; detail: string }) {
  return (
    <div className="validation-gauge" aria-label={`${label}: ${detail}`}>
      <span>{label}</span>
      <div style={{ "--gauge": percentWidth(value) } as CSSProperties}>
        <i />
      </div>
      <strong>{detail}</strong>
    </div>
  );
}
