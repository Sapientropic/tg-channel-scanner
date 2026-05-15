import { Download, GitBranch, RefreshCw } from "lucide-react";

import type { GitUpdateStatus } from "../domain/types";
import { PanelHeader, StatusLine } from "./common";

function countLabel(count: number, singular: string, plural: string) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function updateHeadline(status: GitUpdateStatus | null) {
  if (!status) {
    return {
      tone: "unchecked",
      title: "Automatic checks are on",
      detail: "Desk checks while this page is open.",
    };
  }
  if (status.status === "fetch_failed") {
    return { tone: "blocked", title: "Could not check updates", detail: "Try again when the connection is back." };
  }
  if (status.behind > 0 && status.ahead > 0) {
    return { tone: "blocked", title: "Manual update needed", detail: "Local and remote changes both exist." };
  }
  if (status.behind > 0 && status.dirty && !status.repairable_dirty) {
    return { tone: "blocked", title: "Save local edits first", detail: countLabel(status.dirty_count, "edit is", "edits are") + " in this workspace." };
  }
  if (status.behind > 0) {
    return {
      tone: "ready",
      title: "New version ready",
      detail: status.repairable_dirty
        ? "Generated Desk metadata will be repaired during update."
        : countLabel(status.behind, "app update", "app updates") + " available.",
    };
  }
  if (status.ahead > 0) {
    return { tone: "local", title: "Local version has edits", detail: countLabel(status.ahead, "local commit", "local commits") + " not uploaded." };
  }
  return { tone: "current", title: "Signal Desk is current", detail: "No app update found." };
}

function versionLabel(value: string | null | undefined) {
  return value || "Not checked";
}

function localEditsLabel(status: GitUpdateStatus | null) {
  if (!status) {
    return "Unknown";
  }
  if (status.dirty) {
    if (status.repairable_dirty) {
      return "Generated Desk metadata";
    }
    return countLabel(status.dirty_count, "edit", "edits");
  }
  if (status.ahead > 0) {
    return countLabel(status.ahead, "local commit", "local commits");
  }
  return "None";
}

function repositoryMessage(status: GitUpdateStatus | null) {
  if (!status) return "Checks run every 15 minutes while Desk is open.";
  if (status.desk_build_status === "success") return "Update installed. Desk will refresh this page.";
  if (status.desk_build_status === "failed") return status.desk_build_message || "Update downloaded, but Desk could not rebuild.";
  if (status.status === "fetch_failed") return "Update source could not be reached.";
  if (status.dirty && status.behind > 0 && status.repairable_dirty) return "Update app will repair generated Desk metadata, then install the new version.";
  if (status.dirty && status.behind > 0) return "Save or discard local edits before updating the app.";
  if (status.behind > 0) return "Use Update app to install and refresh Desk.";
  return "Automatic checks stay on while this page is open.";
}

export function StatusRail({
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
  const headline = updateHeadline(gitStatus);
  return (
    <section className="table-section repository-panel" data-update-tone={headline.tone} aria-label="App update controls">
      <PanelHeader icon={<GitBranch size={18} />} title="App updates" />
      <div className="repository-health">
        <span className="repository-status-dot" aria-hidden="true" />
        <div className="repository-health-copy">
          <strong>{headline.title}</strong>
          <span>{headline.detail}</span>
        </div>
        <span className="repository-auto-chip">Auto check</span>
      </div>
      <div className="repository-toolbar">
        <StatusLine label="Current" value={versionLabel(gitStatus?.head)} />
        <StatusLine label="Available" value={versionLabel(gitStatus?.remote_head)} />
        <StatusLine label="Local edits" value={localEditsLabel(gitStatus)} />
        <div className="git-actions">
          <button type="button" onClick={onCheckUpdates} disabled={gitBusy}>
            <RefreshCw size={15} className={gitBusy ? "spin" : undefined} />
            <span>{gitBusy ? "Checking" : "Check now"}</span>
          </button>
          <button className="primary-action" type="button" onClick={onPullLatest} disabled={gitBusy || !gitStatus?.pull_allowed}>
            <Download size={15} />
            <span>Update app</span>
          </button>
        </div>
        <p className={`git-message ${gitStatus?.status || "unchecked"}`}>
          {repositoryMessage(gitStatus)}
        </p>
      </div>
    </section>
  );
}
