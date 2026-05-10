import { type CSSProperties } from "react";
import { Activity, Clock3, ExternalLink } from "lucide-react";

import { EmptyStateShell, PanelHeader } from "./common";
import {
  artifactDisplayName,
  artifactHref,
  artifactShortDetail,
  artifactShortLabel,
  diagnosticTone,
  percentWidth,
  runDisplayDetail,
  runDisplayTitle,
  toneClass,
} from "../domain/display";
import { formatPercent } from "../domain/format";
import {
  formatRunDiagnosticAction,
  formatRunDiagnostics,
  runBucketSignalScore,
  runDayWindowBuckets,
  runHealthDetail,
} from "../domain/projections";
import type { Run } from "../domain/types";

const RECENT_RUN_LIMIT = 8;

type RunHealthDecision = {
  tone: "ok" | "info" | "warn" | "danger";
  headline: string;
  detail: string;
};

export function RunsView({ runs }: { runs: Run[] }) {
  if (!runs.length) {
    return <RunsEmptyState title="No runs yet" detail="Run history is empty in this database." />;
  }
  const visibleRuns = runs.slice(0, RECENT_RUN_LIMIT);
  const archivedRuns = runs.slice(RECENT_RUN_LIMIT);
  return (
    <section className="table-section" aria-label="Run history">
      <PanelHeader icon={<Activity size={18} />} title="Runs" count={runs.length} />
      <RunHealthChart runs={runs} />
      <div className="run-list-head">
        <strong>Recent Evidence</strong>
        <span>
          Latest {visibleRuns.length} of {runs.length}
        </span>
      </div>
      <div className="table-list">
        {visibleRuns.map((run) => (
          <RunRow key={run.run_id} run={run} />
        ))}
      </div>
      {archivedRuns.length > 0 && (
        <details className="run-archive">
          <summary>Older runs ({archivedRuns.length})</summary>
          <div className="table-list">
            {archivedRuns.map((run) => (
              <RunRow key={run.run_id} run={run} />
            ))}
          </div>
        </details>
      )}
    </section>
  );
}

function RunRow({ run }: { run: Run }) {
  const artifact = run.report_artifact ?? null;
  return (
    <div className="table-row run-row">
      <div className="run-primary">
        <strong>{runDisplayTitle(run)}</strong>
        <small>{runDisplayDetail(run)}</small>
      </div>
      <span className={`status ${toneClass(run.status)}`}>{run.status}</span>
      <RunCountBars run={run} />
      <div className="run-health" title={runHealthDetail(run.quality)}>
        <span className={diagnosticTone(run.quality)}>{formatRunDiagnostics(run.quality)}</span>
      </div>
      {artifact ? (
        <a
          className="artifact-link"
          href={artifactHref(artifact.path)}
          aria-label={`Open ${artifactDisplayName(artifact, run)}`}
          rel="noreferrer"
          target="_blank"
          title={artifact.display_path || artifactDisplayName(artifact, run)}
        >
          <ExternalLink size={14} />
          <span>{artifactShortLabel(artifact)}</span>
          <small>{artifactShortDetail(artifact, run)}</small>
        </a>
      ) : (
        <span className="run-report-missing">No report</span>
      )}
    </div>
  );
}

function RunCountBars({ run }: { run: Run }) {
  const cards = run.review_card_count ?? 0;
  const alerts = run.alert_count ?? 0;
  const maxValue = Math.max(1, cards, alerts);
  return (
    <div className="run-count-bars" aria-label={`${cards} cards, ${alerts} alerts`}>
      <span style={{ "--bar": percentWidth(cards / maxValue) } as CSSProperties}>
        <i />
        <b>{cards}</b>
        <em>cards</em>
      </span>
      <span style={{ "--bar": percentWidth(alerts / maxValue) } as CSSProperties}>
        <i />
        <b>{alerts}</b>
        <em>alerts</em>
      </span>
    </div>
  );
}

function RunHealthChart({ runs }: { runs: Run[] }) {
  const recentRuns = runs.slice(0, 80);
  const buckets = runDayWindowBuckets(recentRuns, 7);
  const totalRuns = recentRuns.length;
  const completeRuns = recentRuns.filter((run) => run.status.toLowerCase() === "complete").length;
  const failedRuns = recentRuns.filter((run) => run.status.toLowerCase() === "failed").length;
  const cards = recentRuns.reduce((sum, run) => sum + (run.review_card_count ?? 0), 0);
  const alerts = recentRuns.reduce((sum, run) => sum + (run.alert_count ?? 0), 0);
  const successRate = totalRuns ? completeRuns / totalRuns : 0;
  const decision = buildRunHealthDecision(recentRuns);
  return (
    <div className="run-health-chart" aria-label="Recent run health by day">
      <div className="run-health-summary">
        <small>Run Health</small>
        <strong>{formatPercent(successRate)}</strong>
        <span>complete</span>
        <small>
          {completeRuns} ok / {failedRuns} failed
        </small>
        <small>
          {cards} cards / {alerts} alerts
        </small>
        <div className={`run-health-decision is-${decision.tone}`}>
          <b>{decision.headline}</b>
          <span>{decision.detail}</span>
        </div>
      </div>
      <div className="run-day-bars">
        {buckets.map((bucket) => (
          <div
            className={`run-day-bucket ${bucket.failed ? "has-failure" : ""}`}
            key={bucket.key}
            title={`${bucket.label} · ${bucket.complete} complete · ${bucket.failed} failed · ${bucket.cards} cards · ${bucket.alerts} alerts`}
          >
            <div className="run-day-bar" aria-hidden="true">
              {bucket.failed > 0 && <span className="failed" style={{ height: percentWidth(bucket.failed / bucket.runs) }} />}
              {bucket.complete > 0 && <span className="complete" style={{ height: percentWidth(bucket.complete / bucket.runs) }} />}
              {!bucket.runs && <em />}
              <i style={{ width: percentWidth(runBucketSignalScore(bucket)) }} />
            </div>
            <small>{bucket.label}</small>
          </div>
        ))}
      </div>
    </div>
  );
}

export function buildRunHealthDecision(runs: Run[]): RunHealthDecision {
  const totalRuns = runs.length;
  const failedRuns = runs.filter((run) => run.status.toLowerCase() === "failed").length;
  const cards = runs.reduce((sum, run) => sum + (run.review_card_count ?? 0), 0);
  const alerts = runs.reduce((sum, run) => sum + (run.alert_count ?? 0), 0);
  const diagnosticFailures = runs.reduce((sum, run) => sum + (run.quality?.diagnostic_failure_count ?? 0), 0);
  const diagnosticWarnings = runs.reduce((sum, run) => sum + (run.quality?.diagnostic_warning_count ?? 0), 0);
  const latestIssueCode = runs.find((run) => (run.quality?.diagnostic_count ?? 0) > 0)?.quality?.top_diagnostic_code;

  if (failedRuns > 0) {
    return {
      tone: "danger",
      headline: `Fix ${failedRuns} failed run${failedRuns === 1 ? "" : "s"}`,
      detail: "Treat automation as untrusted until the failed scan is explained.",
    };
  }
  if (diagnosticFailures > 0 || diagnosticWarnings > 0) {
    return {
      tone: diagnosticFailures > 0 ? "danger" : "warn",
      headline: "Diagnostics need attention",
      detail: latestIssueCode
        ? formatRunDiagnosticAction({ diagnostic_count: 1, top_diagnostic_code: latestIssueCode })
        : "Open the latest report diagnostics before tuning profiles.",
    };
  }
  if (alerts > 0) {
    return {
      tone: "info",
      headline: `Review ${alerts} alert candidate${alerts === 1 ? "" : "s"}`,
      detail: `${cards} review card${cards === 1 ? "" : "s"} appeared in recent runs. Clear Review before enabling live alerts.`,
    };
  }
  if (cards > 0) {
    return {
      tone: "info",
      headline: `Review ${cards} card${cards === 1 ? "" : "s"}`,
      detail: "There are signals to triage, but no alert candidate yet.",
    };
  }
  return {
    tone: totalRuns ? "ok" : "info",
    headline: totalRuns ? "No urgent run issue" : "Run history is empty",
    detail: totalRuns ? "Recent scans completed without cards, alerts, or diagnostics." : "Run a local scan before judging source quality.",
  };
}

function RunsEmptyState({
  title,
  detail,
}: {
  title: string;
  detail?: string;
}) {
  return (
    <EmptyStateShell
      icon={<Clock3 size={24} />}
      title={title}
      detail={detail}
      readout={[
        { label: "DB", value: "online" },
        { label: "Run", value: "needed" },
        { label: "Next", value: "local" },
      ]}
    />
  );
}
