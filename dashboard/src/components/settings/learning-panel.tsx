import { useEffect, useMemo, useState } from "react";
import { Copy, Download, FileDiff, Play, RotateCcw, Sparkles, Trash2, UserRoundCog } from "lucide-react";

import { InlineEmpty, PanelHeader } from "../common";
import { feedbackImpactKey, formatActionLabel, toneClass } from "../../domain/display";
import type {
  DashboardNextAction,
  DashboardState,
  FeedbackExportResult,
  FeedbackImpact,
  FeedbackProfileSuggestionsResult,
  Profile,
  ProfileCoachPreview,
} from "../../domain/types";

const FEEDBACK_IMPACT_LIMIT = 4;

export function learningActionLabel(count: number, pendingDraftCount = 0) {
  if (pendingDraftCount > 0) {
    return "Review profile drafts";
  }
  return count > 0 ? "Suggest improvements" : "Review cards";
}

export function feedbackExportStatusLine(result: FeedbackExportResult | null) {
  if (!result) {
    return "";
  }
  const decisionLabel = result.feedback_count === 1 ? "decision" : "decisions";
  return `${result.feedback_count} ${decisionLabel} saved for learning`;
}

export function feedbackSuggestionStatusLine(result: FeedbackProfileSuggestionsResult | null) {
  if (!result) {
    return "";
  }
  const parts = [
    result.created_count ? `${result.created_count} draft${result.created_count === 1 ? "" : "s"} created` : "",
    result.existing_count ? `${result.existing_count} already waiting` : "",
    result.skipped_count ? `${result.skipped_count} skipped` : "",
  ].filter(Boolean);
  return parts.join(" · ") || result.detail || "No profile drafts created";
}

export function LearningPanel({
  summary,
  exportResult,
  suggestionResult,
  exportFeedback,
  generateProfileSuggestions,
  openProfileDrafts,
  openReviewCards,
  clearFeedback,
  undoFeedbackDecision,
  runAgainWithLearning,
  profiles = [],
  profileCoachPreview = null,
  previewProfileCoach,
  createProfileMatchingPreferencesDraft,
  busy,
}: {
  summary?: DashboardState["feedback_summary"];
  exportResult: FeedbackExportResult | null;
  suggestionResult: FeedbackProfileSuggestionsResult | null;
  exportFeedback: () => void;
  generateProfileSuggestions: () => void;
  openProfileDrafts: () => void;
  openReviewCards?: () => void;
  clearFeedback: () => void;
  undoFeedbackDecision: (cardId: string) => void;
  runAgainWithLearning: (profileId?: string) => void;
  profiles?: Profile[];
  profileCoachPreview?: ProfileCoachPreview | null;
  previewProfileCoach?: (profileId: string) => void;
  createProfileMatchingPreferencesDraft?: (profileId: string, preferences: string) => Promise<void> | void;
  busy: boolean;
}) {
  const defaultProfileId = profiles[0]?.profile_id ?? "";
  const [selectedProfileId, setSelectedProfileId] = useState(defaultProfileId);
  useEffect(() => {
    if (!selectedProfileId && defaultProfileId) {
      setSelectedProfileId(defaultProfileId);
    }
  }, [defaultProfileId, selectedProfileId]);
  const exportableCount = summary?.exportable_count ?? exportResult?.feedback_count ?? 0;
  const pendingDraftCount = summary?.pending_profile_diff_count ?? 0;
  const currentDecisionCount = summary?.current_decision_count ?? exportableCount + (summary?.non_exportable_follow_up_count ?? 0);
  const statusLine = feedbackExportStatusLine(exportResult);
  const suggestionLine = feedbackSuggestionStatusLine(suggestionResult);
  const backupPath = exportResult?.output_path || summary?.last_export_path || "";
  const shouldOpenReview = pendingDraftCount <= 0 && currentDecisionCount <= 0;
  const primaryDisabled = busy || (shouldOpenReview && !openReviewCards);
  const hasClearableLearning = currentDecisionCount > 0 || exportableCount > 0 || pendingDraftCount > 0;
  const primaryAction = pendingDraftCount > 0
    ? openProfileDrafts
    : shouldOpenReview
      ? openReviewCards
      : generateProfileSuggestions;
  const copyExportPath = () => {
    if (!backupPath || !navigator.clipboard) {
      return;
    }
    void navigator.clipboard.writeText(backupPath);
  };

  return (
    <div className="table-section feedback-export-panel learning-panel">
      <PanelHeader icon={<FileDiff size={18} />} title="Learning" count={currentDecisionCount} />
      <ProfileCoachLoop
        busy={busy}
        createProfileMatchingPreferencesDraft={createProfileMatchingPreferencesDraft}
        preview={profileCoachPreview}
        previewProfileCoach={previewProfileCoach}
        profiles={profiles}
        runAgainWithLearning={runAgainWithLearning}
        selectedProfileId={selectedProfileId}
        setSelectedProfileId={setSelectedProfileId}
        summary={summary}
      />
      <FeedbackBreakdown summary={summary} exportableCount={exportableCount} />
      {summary?.next_action && <FeedbackNextAction action={summary.next_action} />}
      <FeedbackFlow summary={summary} />
      <FeedbackCalibrationWindow calibration={summary?.calibration} />
      <FeedbackImpactList impacts={summary?.recent_impacts ?? []} undoFeedbackDecision={undoFeedbackDecision} busy={busy} />
      <div className="feedback-export-row feedback-primary-actions">
        <button
          className="text-button"
          type="button"
          onClick={() => primaryAction?.()}
          disabled={primaryDisabled}
        >
          {pendingDraftCount > 0 ? <UserRoundCog size={15} /> : <FileDiff size={15} />}
          <span>{busy ? "Working" : learningActionLabel(currentDecisionCount, pendingDraftCount)}</span>
        </button>
        <button className="text-button secondary" type="button" onClick={clearFeedback} disabled={busy || !hasClearableLearning}>
          <Trash2 size={15} />
          <span>Clear learning decisions</span>
        </button>
      </div>
      {suggestionLine && (
        <div className="feedback-export-result" aria-label="Latest profile suggestions">
          <span className="artifact-chip">{suggestionLine}</span>
          {suggestionResult?.detail && <small>{suggestionResult.detail}</small>}
        </div>
      )}
      {statusLine && (
        <div className="feedback-export-result" aria-label="Latest learning export">
          <span className="artifact-chip">{statusLine}</span>
          <div className="feedback-export-row compact">
            <button className="text-button secondary" type="button" onClick={() => runAgainWithLearning(selectedProfileId || undefined)} disabled={busy}>
              <Play size={15} />
              <span>Run again with learning</span>
            </button>
          </div>
        </div>
      )}
      <details className="settings-evidence feedback-troubleshooting">
        <summary>
          <Download size={16} />
          <span>Advanced backup</span>
        </summary>
        <div className="feedback-export-result">
          <span className="panel-kicker">Learning backup</span>
          <small>{backupPath || "No backup saved yet."}</small>
          <button className="text-button secondary" type="button" onClick={copyExportPath} disabled={!backupPath}>
            <Copy size={15} />
            <span>Copy path</span>
          </button>
          <button className="text-button secondary" type="button" onClick={exportFeedback} disabled={busy || exportableCount <= 0}>
            <Download size={15} />
            <span>Save backup</span>
          </button>
        </div>
      </details>
    </div>
  );
}

function ProfileCoachLoop({
  busy,
  createProfileMatchingPreferencesDraft,
  preview,
  previewProfileCoach,
  profiles,
  runAgainWithLearning,
  selectedProfileId,
  setSelectedProfileId,
  summary,
}: {
  busy: boolean;
  createProfileMatchingPreferencesDraft?: (profileId: string, preferences: string) => Promise<void> | void;
  preview: ProfileCoachPreview | null;
  previewProfileCoach?: (profileId: string) => void;
  profiles: Profile[];
  runAgainWithLearning: (profileId?: string) => void;
  selectedProfileId: string;
  setSelectedProfileId: (profileId: string) => void;
  summary?: DashboardState["feedback_summary"];
}) {
  const selectedProfile = useMemo(
    () => profiles.find((profile) => profile.profile_id === selectedProfileId) ?? profiles[0],
    [profiles, selectedProfileId],
  );
  const coachForSelected = preview?.profile_id === selectedProfile?.profile_id ? preview : null;
  const suggestedRules = coachForSelected?.suggested_preference_rules ?? [];
  const evidenceCounts = coachForSelected?.evidence_counts ?? {
    keep: summary?.by_action?.keep ?? 0,
    skip: summary?.by_action?.skip ?? 0,
    false_positive: summary?.by_action?.false_positive ?? 0,
    follow_up: summary?.non_exportable_follow_up_count ?? 0,
  };
  if (!profiles.length) {
    return null;
  }
  return (
    <section className="profile-coach-panel" aria-label="Profile Coach">
      <div className="feedback-next-action">
        <span className="panel-kicker">Profile Coach</span>
        <strong>Tune this profile from Review choices</strong>
        <small>Suggestions run only when you ask. Nothing changes until you approve a draft.</small>
      </div>
      <div className="feedback-export-row compact">
        <label className="profile-coach-select">
          <span>Profile</span>
          <select
            value={selectedProfile?.profile_id ?? ""}
            onChange={(event) => setSelectedProfileId(event.target.value)}
            disabled={busy}
          >
            {profiles.map((profile) => (
              <option key={profile.profile_id} value={profile.profile_id}>
                {profile.display_name || profile.profile_id}
              </option>
            ))}
          </select>
        </label>
        <button
          className="text-button"
          type="button"
          onClick={() => selectedProfile && previewProfileCoach?.(selectedProfile.profile_id)}
          disabled={busy || !previewProfileCoach || !selectedProfile}
        >
          <Sparkles size={15} />
          <span>{busy ? "Checking" : "Suggest improvements"}</span>
        </button>
      </div>
      <div className="feedback-flow" aria-label="Coach evidence summary">
        <span title="Kept Review cards">
          <strong>{evidenceCounts.keep ?? 0}</strong>
          kept
        </span>
        <span title="Skipped Review cards">
          <strong>{evidenceCounts.skip ?? 0}</strong>
          skipped
        </span>
        <span title="Wrong-match cards">
          <strong>{evidenceCounts.false_positive ?? 0}</strong>
          wrong
        </span>
        <span title="Saved follow-up notes">
          <strong>{evidenceCounts.follow_up ?? 0}</strong>
          notes
        </span>
      </div>
      {coachForSelected ? (
        <div className="profile-coach-preview" aria-label="Profile advice">
          {coachForSelected.diagnosis.map((item) => (
            <div className="feedback-next-action" key={`${item.label}:${item.detail}`}>
              <span className="panel-kicker">{item.label}</span>
              <small>{item.detail}</small>
            </div>
          ))}
          {coachForSelected.suspected_false_positive_patterns.length > 0 && (
            <div className="feedback-breakdown compact">
              {coachForSelected.suspected_false_positive_patterns.map((pattern) => <span key={pattern}>{pattern}</span>)}
            </div>
          )}
          {suggestedRules.length > 0 && (
            <label className="profile-draft-suggestion-field">
              <span>Suggested matching rules</span>
              <textarea readOnly value={suggestedRules.join("\n")} />
            </label>
          )}
          {coachForSelected.warnings.map((warning) => <InlineEmpty key={warning} title={warning} tone="error" />)}
          <div className="feedback-export-row compact">
            <button
              className="text-button"
              type="button"
              disabled={busy || !suggestedRules.length || !selectedProfile || !createProfileMatchingPreferencesDraft}
              onClick={() => selectedProfile && createProfileMatchingPreferencesDraft?.(selectedProfile.profile_id, suggestedRules.join("\n"))}
            >
              <FileDiff size={15} />
              <span>Create draft to review</span>
            </button>
            <button className="text-button secondary" type="button" disabled={busy || !selectedProfile} onClick={() => runAgainWithLearning(selectedProfile?.profile_id)}>
              <Play size={15} />
              <span>Run this profile again</span>
            </button>
          </div>
        </div>
      ) : (
        <InlineEmpty title="No suggestions yet" detail="Save a few Review choices or notes, then ask for suggestions." />
      )}
    </section>
  );
}

function FeedbackFlow({ summary }: { summary?: DashboardState["feedback_summary"] }) {
  const tuningSourceCount =
    summary?.current_decision_count ?? (summary?.exportable_count ?? 0) + (summary?.non_exportable_follow_up_count ?? 0);
  return (
    <div className="feedback-flow" aria-label="Feedback learning flow">
      <span title="Saved Review tags and notes ready for profile tuning">
        <strong>{tuningSourceCount}</strong>
        ready
      </span>
      <span title="Preference drafts waiting for review">
        <strong>{summary?.pending_profile_diff_count ?? 0}</strong>
        pending
      </span>
      <span title="Applied preference drafts">
        <strong>{summary?.applied_profile_diff_count ?? 0}</strong>
        applied
      </span>
      <span title="Reverted preference drafts">
        <strong>{summary?.reverted_profile_diff_count ?? 0}</strong>
        reverted
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
    { label: "Preferred", value: summary?.by_action?.keep ?? 0 },
    { label: "Deprioritized", value: summary?.by_action?.skip ?? 0 },
    { label: "Wrong match", value: summary?.by_action?.false_positive ?? 0 },
    { label: "Saved notes", value: summary?.non_exportable_follow_up_count ?? 0 },
    { label: "High priority", value: summary?.by_rating?.high ?? 0 },
    { label: "Changed", value: summary?.by_decision_status?.changed ?? 0 },
    { label: "Applied changes", value: summary?.applied_profile_diff_count ?? 0 },
    { label: "Reverted changes", value: summary?.reverted_profile_diff_count ?? 0 },
  ].filter((item) => item.value > 0);
  if (!items.length) {
    return <InlineEmpty title={exportableCount > 0 ? "Feedback rows need action labels" : "No learning decisions yet"} />;
  }
  return (
    <div className="feedback-breakdown" aria-label="Feedback calibration evidence">
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
      <span className="panel-kicker">Next step</span>
      <strong>{action.label || "Collect feedback"}</strong>
      {action.detail && <small>{action.detail}</small>}
    </div>
  );
}

function FeedbackCalibrationWindow({ calibration }: { calibration?: NonNullable<DashboardState["feedback_summary"]>["calibration"] }) {
  if (!calibration) {
    return null;
  }
  const highRate = Math.round((calibration.high_rate_after_latest_apply ?? 0) * 100);
  const items = [
    { label: "Runs", value: calibration.runs_after_latest_apply ?? 0 },
    { label: "Cards", value: calibration.cards_after_latest_apply ?? 0 },
    { label: "High", value: calibration.high_cards_after_latest_apply ?? 0 },
    { label: "Wrong", value: calibration.false_positive_after_latest_apply ?? 0 },
    { label: "Feedback", value: calibration.feedback_after_latest_apply ?? 0 },
  ];
  return (
    <div className="feedback-calibration-window" aria-label="Next-run calibration evidence">
      <span className="panel-kicker">After latest update</span>
      <strong>{calibration.next_action?.label || "Collect post-apply evidence"}</strong>
      {calibration.next_action?.detail && <small>{calibration.next_action.detail}</small>}
      <div className="feedback-breakdown compact">
        {items.map((item) => (
          <span key={item.label}>
            {item.label} {item.value}
          </span>
        ))}
        <span>High rate {highRate}%</span>
      </div>
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
