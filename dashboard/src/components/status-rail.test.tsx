import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { StatusRail } from "./status-rail";
import type { GitUpdateStatus } from "../domain/types";

function gitStatus(overrides: Partial<GitUpdateStatus> = {}): GitUpdateStatus {
  return {
    schema_version: "git_update_status_v1",
    status: "behind",
    message: "2 upstream commits available.",
    branch: "main",
    upstream: "origin/main",
    repo_url: "https://github.com/Sapientropic/T-Sense",
    head: "abc123",
    remote_head: "def456",
    ahead: 0,
    behind: 2,
    dirty: false,
    dirty_count: 0,
    pull_allowed: true,
    checked_at: "2026-05-15T00:00:00Z",
    ...overrides,
  };
}

describe("StatusRail", () => {
  it("describes updates as manual before a check runs", () => {
    const html = renderToStaticMarkup(
      <StatusRail
        gitBusy={false}
        gitStatus={null}
        onCheckUpdates={() => undefined}
        onPullLatest={() => undefined}
      />,
    );

    expect(html).toContain("Manual update check");
    expect(html).toContain("Manual check");
    expect(html).toContain("Packaged app builds update through a new app download.");
    expect(html).not.toContain("Automatic checks are on");
    expect(html).not.toContain("Auto check");
  });

  it("explains packaged runtimes that are not Git checkouts", () => {
    const html = renderToStaticMarkup(
      <StatusRail
        gitBusy={false}
        gitStatus={gitStatus({
          status: "not_git_repository",
          message: "This app runtime is not a Git checkout.",
          branch: "unknown",
          upstream: null,
          repo_url: null,
          head: null,
          remote_head: null,
          behind: 0,
          pull_allowed: false,
          fetched: false,
        })}
        onCheckUpdates={() => undefined}
        onPullLatest={() => undefined}
      />,
    );

    expect(html).toContain("Packaged runtime");
    expect(html).toContain("This app copy is not a Git checkout.");
    expect(html).toContain("Dev only");
    expect(html).toContain("This app runtime is not a Git checkout.");
  });

  it("does not promise automatic checks for current development checkouts", () => {
    const html = renderToStaticMarkup(
      <StatusRail
        gitBusy={false}
        gitStatus={gitStatus({
          status: "current",
          message: "Already current.",
          remote_head: "abc123",
          behind: 0,
          pull_allowed: false,
        })}
        onCheckUpdates={() => undefined}
        onPullLatest={() => undefined}
      />,
    );

    expect(html).toContain("Signal Desk is current");
    expect(html).toContain("Manual check");
    expect(html).not.toContain("Automatic checks");
  });

  it("lets ordinary users update through repairable Desk dependency metadata churn", () => {
    const html = renderToStaticMarkup(
      <StatusRail
        gitBusy={false}
        gitStatus={gitStatus({
          dirty: true,
          dirty_count: 1,
          dirty_paths: ["dashboard/package-lock.json"],
          repairable_dirty: true,
          repairable_dirty_count: 1,
          message: "2 upstream commits available. Generated Desk dependency metadata will be repaired during update.",
        })}
        onCheckUpdates={() => undefined}
        onPullLatest={() => undefined}
      />,
    );

    expect(html).toContain("New version ready");
    expect(html).toContain("Generated Desk metadata will be repaired during update.");
    expect(html).toContain("Generated Desk metadata");
    expect(html).toContain("Update app");
    expect(html).not.toContain("Save local edits first");
    expect(html).not.toContain("disabled=\"\"");
  });
});
