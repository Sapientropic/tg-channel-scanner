import { ArchiveRestore, ClipboardList, Database, FileDown, FolderOpen, ListChecks, RefreshCcw, ShieldCheck } from "lucide-react";

import { CopyableCommand, InlineEmpty, PanelHeader } from "../common";
import type { DeskSupportDiagnosticExportResult, DeskSupportStatus } from "../../domain/types";

export function SupportPanel({
  status,
  error,
  onRefresh,
  onExportDiagnostics,
  onRevealTarget,
  exportResult,
}: {
  status: DeskSupportStatus | null;
  error: string | null;
  onRefresh: () => void;
  onExportDiagnostics?: () => void;
  onRevealTarget?: (target: string) => void;
  exportResult?: DeskSupportDiagnosticExportResult | null;
}) {
  const summary = status ? supportSummary(status) : "";
  const legacyLocations = status?.migration?.legacy_locations ?? [];
  return (
    <div className="table-section support-panel" aria-label="Support diagnostics">
      <PanelHeader icon={<ClipboardList size={18} />} title="Support" count={status?.recovery.length ?? 0} />
      {error && <InlineEmpty title="Support diagnostics unavailable" detail={error} tone="warning" />}
      {!status && !error && <InlineEmpty title="Loading support diagnostics" />}
      {status && (
        <>
          <div className="support-summary" aria-label="Support summary">
            <div>
              <span className="panel-kicker">Local workspace</span>
              <strong>{status.dashboard_url}</strong>
              <small>{status.platform}</small>
            </div>
            <button className="text-button secondary" onClick={onRefresh} type="button">
              <RefreshCcw size={15} />
              <span>Refresh</span>
            </button>
          </div>

          <div className="support-path-grid" aria-label="Local app paths">
            {status.paths.map((item) => (
              <article className="support-path-card" data-exists={item.exists ? "true" : "false"} key={item.label}>
                <div>
                  <strong>{item.label}</strong>
                  <span>{item.exists ? "Found" : "Not created yet"}</span>
                </div>
                <small>{item.detail}</small>
                <div className="support-path-actions">
                  <CopyableCommand command={item.path} label={item.label} compact copyLabel="Copy path" />
                  {item.target && onRevealTarget && (
                    <button
                      aria-label={`Open in Finder: ${item.label}`}
                      className="text-button secondary support-reveal-button"
                      onClick={() => onRevealTarget(item.target ?? "")}
                      title="Open in Finder"
                      type="button"
                    >
                      <FolderOpen size={14} />
                      <span>Reveal</span>
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>

          {status.readiness && (
            <section className="support-readiness" aria-label="Ready for real scan">
              <PanelHeader
                icon={<ListChecks size={18} />}
                title="Ready For Real Scan"
                count={status.readiness.ready_count}
              />
              <p className="support-readiness-summary">{status.readiness.summary}</p>
              <div className="support-readiness-list">
                {status.readiness.items.map((item) => (
                  <article className="support-readiness-row" data-status={item.status} key={item.label}>
                    <div>
                      <strong>{item.label}</strong>
                      <small>{item.detail}</small>
                      {item.next_action && <em>{item.next_action}</em>}
                    </div>
                    <span>{supportReadinessStatusLabel(item.status)}</span>
                  </article>
                ))}
              </div>
            </section>
          )}

          <section className="support-boundaries" aria-label="Data boundaries">
            <PanelHeader icon={<ShieldCheck size={18} />} title="Data Boundaries" />
            <div className="support-boundary-grid">
              {status.data_boundaries.map((item) => (
                <article className="support-boundary-card" data-external={item.external ? "true" : "false"} key={item.label}>
                  <strong>{item.label}</strong>
                  <span>{item.external ? "External when run" : "Local by default"}</span>
                  <small>{item.detail}</small>
                </article>
              ))}
            </div>
          </section>

          {status.migration && legacyLocations.length > 0 && (
            <section className="support-migration" aria-label="Legacy project data">
              <PanelHeader icon={<ArchiveRestore size={18} />} title="Legacy Data" count={legacyLocations.length} />
              <p className="support-migration-detail">{status.migration.detail}</p>
              <div className="support-recovery-list">
                {legacyLocations.map((item) => (
                  <article className="support-recovery-row" data-exists={item.exists ? "true" : "false"} key={item.label}>
                    <div>
                      <strong>{item.label}</strong>
                      <small>{item.detail}</small>
                    </div>
                    <CopyableCommand command={item.path} label={item.label} compact copyLabel="Copy path" iconOnly />
                  </article>
                ))}
              </div>
              <small className="support-migration-next">{status.migration.next_action}</small>
            </section>
          )}

          <section className="support-recovery" aria-label="Recovery checks">
            <PanelHeader icon={<Database size={18} />} title="Recovery" />
            <div className="support-recovery-list">
              {status.recovery.map((item) => (
                <article className="support-recovery-row" key={item.label}>
                  <div>
                    <strong>{item.label}</strong>
                    <small>{item.detail}</small>
                  </div>
                  {item.path && <CopyableCommand command={item.path} label={item.label} compact copyLabel="Copy path" iconOnly />}
                </article>
              ))}
            </div>
          </section>

          <div className="support-export" aria-label="Support snapshot">
            <CopyableCommand command={summary} label="support summary" compact copyLabel="Copy summary" />
            {onExportDiagnostics && (
              <button className="text-button secondary" onClick={onExportDiagnostics} type="button">
                <FileDown size={15} />
                <span>Save snapshot</span>
              </button>
            )}
            {exportResult && (
              <CopyableCommand command={exportResult.output_path} label="support snapshot file" compact copyLabel="Copy snapshot path" />
            )}
          </div>
        </>
      )}
    </div>
  );
}

function supportReadinessStatusLabel(status: string) {
  if (status === "ready") {
    return "Ready";
  }
  if (status === "needs_user") {
    return "Needs setup";
  }
  return status || "Unknown";
}

export function supportSummary(status: DeskSupportStatus) {
  const lines = [
    "T-Sense support snapshot",
    `Checked: ${status.checked_at}`,
    `Dashboard: ${status.dashboard_url}`,
    `App data: ${status.app_data_root}`,
    `Database: ${status.database_path}`,
    `Reports: ${status.output_dir}`,
    `Desktop log: ${status.desktop_log_path}`,
    `Telegram config: ${status.telegram_config_dir}`,
  ];
  if (status.migration?.legacy_locations.length) {
    lines.push(`Migration: ${status.migration.status}`);
    status.migration.legacy_locations.forEach((item) => {
      lines.push(`Legacy ${item.label}: ${item.path}`);
    });
  }
  if (status.readiness) {
    lines.push(`Readiness: ${status.readiness.summary}`);
  }
  return lines.join("\n");
}
