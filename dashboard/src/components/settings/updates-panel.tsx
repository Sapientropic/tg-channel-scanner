import { StatusRail } from "../status-rail";
import type { GitUpdateStatus } from "../../domain/types";

export function UpdatesPanel({
  gitBusy,
  gitStatus,
  onCheckUpdates,
  onPullLatest,
}: {
  gitBusy: boolean;
  gitStatus: GitUpdateStatus | null;
  onCheckUpdates: () => void;
  onPullLatest: () => void;
}) {
  return <StatusRail gitBusy={gitBusy} gitStatus={gitStatus} onCheckUpdates={onCheckUpdates} onPullLatest={onPullLatest} />;
}
