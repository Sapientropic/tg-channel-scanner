import { useCallback, useEffect, useRef, useState } from "react";

import { checkGitUpdates as checkGitUpdatesRequest, errorMessage, pullLatestGit } from "../api/client";
import type { GitUpdateStatus } from "../domain/types";

type Notice = { tone: "success" | "error"; text: string } | null;

export function useGitActions({ setNotice }: { setNotice: (notice: Notice) => void }) {
  const [gitBusy, setGitBusy] = useState(false);
  const [gitStatus, setGitStatus] = useState<GitUpdateStatus | null>(null);
  const checkInFlight = useRef(false);
  const mounted = useRef(true);

  const runCheck = useCallback(
    async ({ manual }: { manual: boolean }) => {
      if (checkInFlight.current) {
        return;
      }
      checkInFlight.current = true;
      if (manual) {
        setGitBusy(true);
        setNotice(null);
      }
      try {
        const git = await checkGitUpdatesRequest();
        if (!mounted.current) {
          return;
        }
        setGitStatus(git);
        if (manual) {
          setNotice({
            tone: "success",
            text: git.behind > 0 ? "New Signal Desk version is ready" : "Signal Desk is up to date",
          });
        }
      } catch (error) {
        if (manual && mounted.current) {
          setNotice({ tone: "error", text: errorMessage(error) });
        }
      } finally {
        checkInFlight.current = false;
        if (manual && mounted.current) {
          setGitBusy(false);
        }
      }
    },
    [setNotice],
  );

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  function checkUpdates() {
    void runCheck({ manual: true });
  }

  async function pullLatest() {
    if (!gitStatus?.pull_allowed) {
      return;
    }
    const repairNote = gitStatus.repairable_dirty
      ? " Signal Desk will repair generated dependency metadata first; real local edits still block updates."
      : "";
    const confirmed = window.confirm(
      `Update Signal Desk now? This downloads the app update, rebuilds Desk locally, then refreshes this page.${repairNote} Local edits must be saved first.`,
    );
    if (!confirmed) {
      return;
    }
    setGitBusy(true);
    setNotice(null);
    try {
      const git = await pullLatestGit();
      setGitStatus(git);
      if (git.desk_build_status === "failed") {
        const detail = git.desk_build_message ? ` ${git.desk_build_message}` : "";
        setNotice({ tone: "error", text: `Update downloaded, but Desk could not rebuild.${detail}` });
        return;
      }
      if (git.desk_reload_recommended) {
        const reloadDelayMs = git.desk_restart_scheduled ? Math.max(git.desk_reload_delay_ms ?? 2500, 1500) : 900;
        setNotice({
          tone: "success",
          text: git.desk_restart_scheduled ? "Signal Desk updated. Restarting local server..." : "Signal Desk updated. Reloading...",
        });
        window.setTimeout(() => window.location.reload(), reloadDelayMs);
        return;
      }
      setNotice({ tone: "success", text: "Signal Desk updated" });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setGitBusy(false);
    }
  }

  return { gitBusy, gitStatus, checkUpdates, pullLatest };
}
