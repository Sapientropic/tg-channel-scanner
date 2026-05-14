import { Check, FileDiff, RefreshCw } from "lucide-react";

import { toneClass } from "../../domain/display";
import { formatDate, profileDisplayName } from "../../domain/format";
import type { ProfilePatch } from "../../domain/types";
import { parseDiff } from "./diff";

export function ProfilePatchCard({
  patch,
  applyPatch,
  revertPatch,
  replayPatch,
  busy,
}: {
  patch: ProfilePatch;
  applyPatch: (patchId: string) => void;
  revertPatch: (patchId: string) => void;
  replayPatch: (patchId: string) => void;
  busy: boolean;
}) {
  const { added, removed } = parseDiff(patch.diff_text || "");
  const draftSummary = profileDraftUserSummary(patch);
  const readiness = patch.apply_readiness;
  const readinessStatus = readiness?.status || "";
  const showReadiness = Boolean(readiness && readinessStatus !== "ready");
  const applyBlocked = patch.status === "pending" && Boolean(readinessStatus && readinessStatus !== "ready");
  return (
    <article className="review-card patch-card">
      <div className="card-main">
        <div className="card-title-row">
          <h3>{profilePatchTitle(patch)}</h3>
          <span className={`status ${toneClass(patch.status)}`}>{patch.status}</span>
        </div>
        <div className="patch-context-row">
          <span>{draftSourceLabel(patch)}</span>
          <span>{formatDate(patch.created_at)}</span>
          {added.length > 0 && <span>{added.length} added</span>}
          {removed.length > 0 && <span>{removed.length} removed</span>}
        </div>
        {showReadiness && (
          <div className={`patch-readiness ${toneClass(readiness?.status || "unknown")}`}>
            <strong>{readiness?.label || "Readiness check"}</strong>
            {readiness?.detail && <span>{readiness.detail}</span>}
          </div>
        )}
        <p className="note-line">{draftSummary}</p>
        <details className="patch-diff-details">
          <summary>
            <FileDiff size={14} />
            <span>Preview</span>
          </summary>
          <div className="visual-diff">
            {added.length > 0 && (
              <div className="diff-added">
                <strong>Added rules</strong>
                <ul>
                  {added.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {removed.length > 0 && (
              <div className="diff-removed">
                <strong>Removed rules</strong>
                <ul>
                  {removed.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {added.length === 0 && removed.length === 0 && (
              <p>No readable rule changes were found. Use expert details before applying.</p>
            )}
            <details className="expert-diff-details">
              <summary>Expert raw change</summary>
              <pre>{patch.diff_text || "No raw change recorded."}</pre>
            </details>
          </div>
        </details>
        <div className="patch-actions">
          {patch.status === "pending" && (
            <button
              className="text-button"
              type="button"
              onClick={() => applyPatch(patch.patch_id)}
              disabled={busy || applyBlocked}
              title="Apply this draft to the local profile file after checking it."
            >
              <Check size={15} />
              <span>{applyButtonLabel(patch)}</span>
            </button>
          )}
          {patch.status === "applied" && (
            <button
              className="text-button"
              type="button"
              onClick={() => revertPatch(patch.patch_id)}
              disabled={busy}
              title="Restore the saved profile snapshot if the file has not changed"
            >
              <RefreshCw size={15} />
              <span>Revert</span>
            </button>
          )}
          {patch.status === "reverted" && (
            <button
              className="text-button"
              type="button"
              onClick={() => replayPatch(patch.patch_id)}
              disabled={busy}
              title="Create a fresh pending profile change if the file still matches the saved snapshot"
            >
              <RefreshCw size={15} />
              <span>Replay</span>
            </button>
          )}
        </div>
      </div>
    </article>
  );
}

function profilePatchTitle(patch: ProfilePatch) {
  const sourceCount = patch.source_card_count || 0;
  if (sourceCount > 1) {
    return `${profileDisplayName(patch.profile_id)} feedback batch`;
  }
  return patch.card_title || profileDisplayName(patch.profile_id);
}

function draftSourceLabel(patch: ProfilePatch) {
  const sourceCount = patch.source_card_count || 0;
  if (sourceCount > 1) {
    return `${sourceCount} Review decisions`;
  }
  if (sourceCount === 1 || patch.card_id) {
    return "1 Review decision";
  }
  return "Profile draft";
}

function applyButtonLabel(patch: ProfilePatch) {
  return (patch.source_card_count || 0) > 1 ? "Apply batch" : "Apply";
}

function profileDraftUserSummary(patch: ProfilePatch) {
  const note = patch.note || "";
  const sourceCount = patch.source_card_count || 0;
  if (!note) {
    return "Profile rule change awaiting review.";
  }
  if (sourceCount > 1) {
    return `Combines ${sourceCount} Review decisions into reusable matching rules for future scans.`;
  }
  if (sourceCount === 1 || patch.card_id) {
    return "Turns this Review decision into a reusable matching rule for future scans.";
  }
  if (note.startsWith("Desk feedback tuning")) {
    return "Summarizes confirmed Review decisions into reusable matching rules.";
  }
  if (note.startsWith("User edited matching preferences")) {
    return "Updates the editable matching rules for future scans.";
  }
  return note;
}
