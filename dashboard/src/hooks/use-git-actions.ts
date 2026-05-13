import { useState } from "react";

import { checkGitUpdates as checkGitUpdatesRequest, errorMessage, pullLatestGit } from "../api/client";
import type { GitUpdateStatus } from "../domain/types";

type Notice = { tone: "success" | "error"; text: string } | null;

export function useGitActions({ setNotice }: { setNotice: (notice: Notice) => void }) {
  const [gitBusy, setGitBusy] = useState(false);
  const [gitStatus, setGitStatus] = useState<GitUpdateStatus | null>(null);

  async function checkUpdates() {
    setGitBusy(true);
    setNotice(null);
    try {
      const git = await checkGitUpdatesRequest();
      setGitStatus(git);
      setNotice({ tone: "success", text: "Remote status checked" });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setGitBusy(false);
    }
  }

  async function pullLatest() {
    if (!gitStatus?.pull_allowed) {
      return;
    }
    const confirmed = window.confirm("Pull latest with git pull --ff-only? Local changes must already be clean.");
    if (!confirmed) {
      return;
    }
    setGitBusy(true);
    setNotice(null);
    try {
      const git = await pullLatestGit();
      setGitStatus(git);
      setNotice({ tone: "success", text: "Pulled latest upstream changes" });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setGitBusy(false);
    }
  }

  return { gitBusy, gitStatus, checkUpdates, pullLatest };
}
