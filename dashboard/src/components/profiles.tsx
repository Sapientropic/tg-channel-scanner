import { useEffect, useState } from "react";
import {
  Bell,
  BellOff,
  Check,
  ChevronDown,
  CircleHelp,
  CirclePause,
  CirclePlay,
  FileDiff,
  FileUp,
  Plus,
  RefreshCw,
  Save,
  SlidersHorizontal,
  Sun,
  UserRoundCog,
} from "lucide-react";

import { InlineEmpty, PanelHeader } from "./common";
import { alertMode, diffStats, toneClass } from "../domain/display";
import { formatDate, formatScanWindow, profileDisplayName, titleCaseLabel } from "../domain/format";
import type { Profile, ProfileCreateResult, ProfilePatch, ProfileRuntimeSettings } from "../domain/types";

export function ProfilesView({
  profiles,
  patches,
  applyPatch,
  revertPatch,
  replayPatch,
  setAlertMode,
  setProfileEnabled,
  setProfileRuntimeSettings,
  createProfileDraftNote,
  createProfileMatchingPreferencesDraft,
  createProfileFromBrief,
  profileCreateResult,
  busy,
  onOpenStart,
}: {
  profiles: Profile[];
  patches: ProfilePatch[];
  applyPatch: (patchId: string) => void;
  revertPatch: (patchId: string) => void;
  replayPatch: (patchId: string) => void;
  setAlertMode: (profileId: string, mode: string) => void;
  setProfileEnabled: (profileId: string, enabled: boolean) => void;
  setProfileRuntimeSettings: (profileId: string, settings: ProfileRuntimeSettings) => void;
  createProfileDraftNote: (profileId: string, note: string) => Promise<void>;
  createProfileMatchingPreferencesDraft: (profileId: string, preferences: string) => Promise<void>;
  createProfileFromBrief: (payload: {
    brief: string;
    source_filename?: string;
    source_text?: string;
    source_base64?: string;
  }) => Promise<ProfileCreateResult>;
  profileCreateResult: ProfileCreateResult | null;
  busy: boolean;
  onOpenStart?: () => void;
}) {
  const [draftsOpen, setDraftsOpen] = useState(() => shouldOpenDraftsByDefault());
  const draftsPanelId = "profile-drafts-panel";
  return (
    <section className="split-section profiles-section" data-has-drafts={patches.length > 0 ? "true" : "false"}>
      <div className="plain-panel">
        <PanelHeader icon={<UserRoundCog size={18} />} title="Profiles" />
        <NewProfilePanel
          busy={busy}
          createProfileFromBrief={createProfileFromBrief}
          latestResult={profileCreateResult}
        />
        {profiles.length ? (
          <div className="table-list">
            {profiles.map((profile) => (
              <ProfileRow
                busy={busy}
                createProfileDraftNote={createProfileDraftNote}
                createProfileMatchingPreferencesDraft={createProfileMatchingPreferencesDraft}
                key={profile.profile_id}
                profile={profile}
                setAlertMode={setAlertMode}
                setProfileEnabled={setProfileEnabled}
                setProfileRuntimeSettings={setProfileRuntimeSettings}
              />
            ))}
          </div>
        ) : (
          <InlineEmpty
            title="No profiles yet"
            detail="Create or import a monitor before Review can produce useful cards."
            action={
              onOpenStart ? (
                <button type="button" onClick={onOpenStart}>
                  <CirclePlay size={15} />
                  <span>Open setup</span>
                </button>
              ) : undefined
            }
          />
        )}
      </div>
      {patches.length > 0 && (
        <div className="plain-panel profile-drafts-panel" data-collapsed={draftsOpen ? "false" : "true"}>
          <header className="panel-header profile-drafts-header">
            <button
              aria-controls={draftsPanelId}
              aria-expanded={draftsOpen}
              className="profile-drafts-toggle"
              onClick={() => setDraftsOpen((value) => !value)}
              type="button"
            >
              <span className="panel-title">
                <FileDiff size={18} />
                Profile Drafts
              </span>
              <span className="profile-drafts-toggle-copy">{draftsOpen ? "Collapse" : "Review drafts"}</span>
              <ChevronDown size={17} />
            </button>
            <span className="count-badge">{patches.length}</span>
          </header>
          <div className="patch-list" hidden={!draftsOpen} id={draftsPanelId}>
            {patches.map((patch) => (
              <ProfilePatchCard
                applyPatch={applyPatch}
                busy={busy}
                key={patch.patch_id}
                patch={patch}
                replayPatch={replayPatch}
                revertPatch={revertPatch}
              />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function NewProfilePanel({
  busy,
  createProfileFromBrief,
  latestResult,
}: {
  busy: boolean;
  createProfileFromBrief: (payload: {
    brief: string;
    source_filename?: string;
    source_text?: string;
    source_base64?: string;
  }) => Promise<ProfileCreateResult>;
  latestResult: ProfileCreateResult | null;
}) {
  const [open, setOpen] = useState(false);
  const [brief, setBrief] = useState("");
  const [filePayload, setFilePayload] = useState<{ name: string; text?: string; base64?: string } | null>(null);
  const [localError, setLocalError] = useState("");
  const hasInput = Boolean(brief.trim() || filePayload);

  async function handleFile(file: File | null) {
    setLocalError("");
    setFilePayload(null);
    if (!file) {
      return;
    }
    const suffix = file.name.split(".").pop()?.toLowerCase() ?? "";
    if (!["md", "markdown", "txt", "pdf"].includes(suffix)) {
      setLocalError("Use a Markdown, text, or PDF profile file.");
      return;
    }
    if (file.size > 4 * 1024 * 1024) {
      setLocalError("Use a file under 4 MB.");
      return;
    }
    try {
      const payload = suffix === "pdf"
        ? { name: file.name, base64: await readFileAsDataUrl(file) }
        : { name: file.name, text: await readFileAsText(file) };
      setFilePayload(payload);
    } catch {
      setLocalError("Signal Desk could not read that file.");
    }
  }

  async function submitProfile() {
    if (!hasInput || busy) {
      return;
    }
    setLocalError("");
    try {
      await createProfileFromBrief({
        brief: brief.trim(),
        source_filename: filePayload?.name,
        source_text: filePayload?.text,
        source_base64: filePayload?.base64,
      });
      setBrief("");
      setFilePayload(null);
      setOpen(false);
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : "Profile creation failed.");
    }
  }

  return (
    <section className="new-profile-panel" data-open={open ? "true" : "false"} aria-label="Create a profile">
      <button className="new-profile-toggle" type="button" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        <Plus size={15} />
        <span>New profile</span>
        <small>Paste a plain-language goal or import Markdown, text, or PDF.</small>
      </button>
      {open && (
        <div className="new-profile-body">
          <label>
            <span>What should Signal Desk watch for?</span>
            <textarea
              value={brief}
              onChange={(event) => setBrief(event.target.value)}
              disabled={busy}
              placeholder="Example: Watch for senior remote AI engineering roles, paid agent projects, or founder requests that match my background. Avoid unpaid internships and vague promos."
            />
          </label>
          <label className="new-profile-file">
            <FileUp size={15} />
            <span>{filePayload ? filePayload.name : "Attach Markdown, text, or PDF"}</span>
            <input
              type="file"
              accept=".md,.markdown,.txt,.pdf,text/markdown,text/plain,application/pdf"
              disabled={busy}
              onChange={(event) => void handleFile(event.target.files?.[0] ?? null)}
            />
          </label>
          <div className="new-profile-actions">
            <button className="text-button profile-primary-action" type="button" disabled={busy || !hasInput} onClick={() => void submitProfile()}>
              <Check size={15} />
              <span>{busy ? "Creating" : "Create profile"}</span>
            </button>
            <button className="text-button secondary" type="button" disabled={busy} onClick={() => setOpen(false)}>
              <span>Cancel</span>
            </button>
          </div>
          <small className="new-profile-note">
            Signal Desk creates a local profile first. Review its matching rules before using it for automation.
          </small>
          {localError && <InlineEmpty title={localError} tone="error" />}
        </div>
      )}
      {!open && latestResult && (
        <div className="new-profile-result">
          <strong>{latestResult.display_name}</strong>
          <span>{latestResult.detail}</span>
        </div>
      )}
    </section>
  );
}

function readFileAsText(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsText(file);
  });
}

function readFileAsDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

function ProfileRow({
  profile,
  setAlertMode,
  setProfileEnabled,
  setProfileRuntimeSettings,
  createProfileDraftNote,
  createProfileMatchingPreferencesDraft,
  busy,
}: {
  profile: Profile;
  setAlertMode: (profileId: string, mode: string) => void;
  setProfileEnabled: (profileId: string, enabled: boolean) => void;
  setProfileRuntimeSettings: (profileId: string, settings: ProfileRuntimeSettings) => void;
  createProfileDraftNote: (profileId: string, note: string) => Promise<void>;
  createProfileMatchingPreferencesDraft: (profileId: string, preferences: string) => Promise<void>;
  busy: boolean;
}) {
  const [open, setOpen] = useState(() => shouldOpenProfileByDefault());
  const profileName = profile.display_name || profileDisplayName(profile.profile_id);
  return (
    <details
      className={`table-row profile-row ${profile.enabled ? "" : "paused"}`}
      onToggle={(event) => setOpen(event.currentTarget.open)}
      open={open}
    >
      <summary className="profile-summary" aria-label={`${profileName} profile summary`}>
        <span className="profile-summary-title">
          <strong>{profileName}</strong>
          <span className={profile.enabled ? "status enabled" : "status disabled"}>
            {profile.enabled ? "Monitoring" : "Paused"}
          </span>
        </span>
        <span className="profile-summary-meta" aria-label={`Quick settings for ${profileName}`}>
          <span>{profileScanWindowLabel(profile)}</span>
          <span>{profileItemLimitLabel(profile)}</span>
          <span>{profileTopicLabel(profile)}</span>
        </span>
        <span className="profile-summary-toggle">{open ? "Collapse" : "View / edit"}</span>
      </summary>
      <div className="profile-row-body">
        <ProfileMatchingPanel profile={profile} />
        <div className="profile-rhythm" aria-label={`Profile settings for ${profileName}`}>
          <span title="How far back each scan checks">{profileScanWindowLabel(profile)}</span>
          <span title="Maximum messages reviewed per scan">{profileItemLimitLabel(profile)}</span>
          <span title="Source group used by this monitor">{profileTopicLabel(profile)}</span>
          <span title="Notification destinations configured">{profileNotificationLabel(profile)}</span>
        </div>
        <div className="profile-control-groups">
          <div className="profile-control-group">
            <span className="profile-control-label">Monitoring</span>
            <ProfileEnabledControl profile={profile} setProfileEnabled={setProfileEnabled} busy={busy} />
          </div>
          <div className="profile-control-group">
            <span className="profile-control-label">
              Notifications
              <ProfileHelpTip text="Choose when this profile can notify you. This does not change what Signal Desk scans." />
            </span>
            <AlertModeControl profile={profile} setAlertMode={setAlertMode} busy={busy} />
            {!profile.enabled && <span className="profile-paused-note">Resume monitoring to adjust alerts.</span>}
          </div>
        </div>
        <ProfileRuntimeSettingsControl
          profile={profile}
          setProfileRuntimeSettings={setProfileRuntimeSettings}
          createProfileDraftNote={createProfileDraftNote}
          createProfileMatchingPreferencesDraft={createProfileMatchingPreferencesDraft}
          busy={busy}
        />
      </div>
    </details>
  );
}

function ProfileMatchingPanel({ profile }: { profile: Profile }) {
  const [open, setOpen] = useState(() => shouldOpenMatchingByDefault());
  const sections = profile.matching_profile?.sections ?? [];
  if (!sections.length) {
    return (
      <div className="profile-matching-panel is-empty">
        <span className="panel-kicker">Matching profile</span>
        <strong>No readable matching rules yet</strong>
        <p>Edit this profile to add plain-language rules Signal Desk can use.</p>
      </div>
    );
  }
  const primarySections = sections.filter((section) => section.key !== "report").slice(0, 3);
  const extraSections = sections.filter((section) => !primarySections.includes(section));
  return (
    <details
      className="profile-matching-panel"
      aria-label={`Matching rules for ${profile.display_name || profileDisplayName(profile.profile_id)}`}
      onToggle={(event) => setOpen(event.currentTarget.open)}
      open={open}
    >
      <summary className="profile-matching-head">
        <span className="panel-kicker">Matching profile</span>
        <strong>{profile.matching_profile?.summary || "Current rules used for matching"}</strong>
        <small>{open ? "Collapse rules" : "View rules"}</small>
      </summary>
      <div className="profile-matching-body">
        <div className="profile-matching-grid">
          {primarySections.map((section) => (
            <section className={`profile-match-section is-${section.key}`} key={section.key}>
              <span>{section.label}</span>
              <ul>
                {section.items.slice(0, section.key === "rules" ? 4 : 3).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </section>
          ))}
        </div>
        {extraSections.length > 0 && (
          <details className="profile-matching-more">
            <summary>More matching context</summary>
            {extraSections.map((section) => (
              <section key={section.key}>
                <span>{section.label}</span>
                <ul>
                  {section.items.slice(0, 5).map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>
            ))}
          </details>
        )}
      </div>
    </details>
  );
}

function shouldOpenMatchingByDefault() {
  if (typeof window === "undefined") {
    return true;
  }
  return window.innerWidth > 680;
}

function shouldOpenProfileByDefault() {
  if (typeof window === "undefined") {
    return true;
  }
  return window.innerWidth > 680;
}

function shouldOpenDraftsByDefault() {
  if (typeof window === "undefined") {
    return true;
  }
  return window.innerWidth > 680;
}

function parseDiff(diffText: string) {
  const lines = diffText.split("\n");
  const added: string[] = [];
  const removed: string[] = [];
  for (const line of lines) {
    if (line.startsWith("@@") || line.startsWith("---") || line.startsWith("+++")) {
      continue;
    }
    if (line.startsWith("+")) {
      const item = cleanDiffLine(line.substring(1));
      if (item) {
        added.push(item);
      }
    } else if (line.startsWith("-")) {
      const item = cleanDiffLine(line.substring(1));
      if (item) {
        removed.push(item);
      }
    }
  }
  return { added, removed };
}

function cleanDiffLine(line: string) {
  const cleaned = line
    .replace(/^\s*[-*]\s+/, "")
    .replace(/^\s*\+\s*/, "")
    .replace(/\*\*([^*]+)\*\*/g, "$1")
    .trim();
  if (!cleaned || cleaned === "## Follow-up Preferences") {
    return "";
  }
  if (cleaned.startsWith("Desk feedback tuning: prefer matches like")) {
    return "Extract broad matching preferences from your confirmed Review choices.";
  }
  if (cleaned.startsWith("Desk feedback tuning: Analyze")) {
    return "Turn Keep / Skip / Wrong Match decisions into reusable matching rules.";
  }
  return cleaned;
}

function ProfilePatchCard({
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
  const draftSummary = profileDraftUserSummary(patch.note);
  return (
    <article className="review-card patch-card">
      <div className="card-main">
        <div className="card-title-row">
          <h3>{patch.card_title || profileDisplayName(patch.profile_id)}</h3>
          <span className={`status ${toneClass(patch.status)}`}>{patch.status}</span>
        </div>
        <div className="patch-context-row">
          <span>Profile change</span>
          <span>{formatDate(patch.created_at)}</span>
          {added.length > 0 && <span>{added.length} added</span>}
          {removed.length > 0 && <span>{removed.length} removed</span>}
        </div>
        {patch.apply_readiness && (
          <div className={`patch-readiness ${toneClass(patch.apply_readiness.status || "unknown")}`}>
            <strong>{patch.apply_readiness.label || "Readiness check"}</strong>
            {patch.apply_readiness.detail && <span>{patch.apply_readiness.detail}</span>}
          </div>
        )}
        <div className="patch-user-explainer">
          <strong>{profileDraftEffectTitle(patch.note)}</strong>
          <p>{profileDraftEffectDetail(patch.note)}</p>
        </div>
        <p className="note-line">{draftSummary}</p>
        <details className="patch-diff-details">
          <summary>
            <FileDiff size={14} />
            <span>Preview changes</span>
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
              <summary>Expert raw diff</summary>
              <pre>{patch.diff_text || "No diff body recorded."}</pre>
            </details>
          </div>
        </details>
        <div className="patch-actions">
          {patch.status === "pending" && (
            <button
              className="text-button"
              type="button"
              onClick={() => applyPatch(patch.patch_id)}
              disabled={busy}
              title="Apply this draft to the local profile file after checking it."
            >
              <Check size={15} />
              <span>Apply to profile</span>
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
              title="Create a fresh pending diff from this reverted profile change if the file still matches the saved snapshot"
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

function profileDraftEffectTitle(note: string) {
  if (note.startsWith("User edited matching preferences")) {
    return "Updates your matching rules";
  }
  return note.startsWith("Desk feedback tuning") ? "Learns from your Review choices" : "Adds your manual preference";
}

function profileDraftEffectDetail(note: string) {
  if (note.startsWith("Desk feedback tuning")) {
    return "Signal Desk should generalize your Keep, Skip, and Wrong Match decisions into reusable rules. It should not copy single card titles as permanent preferences.";
  }
  if (note.startsWith("User edited matching preferences")) {
    return "Apply this after checking the preview. Future scans will use these plain-language rules when ranking matches.";
  }
  return "Apply this after checking it. Future scans will use this background or preference note when ranking matches for this profile.";
}

function profileDraftUserSummary(note: string) {
  if (!note) {
    return "Profile rule change awaiting review.";
  }
  if (note.startsWith("Desk feedback tuning")) {
    return "Draft from learning loop: extract broad rules from confirmed Review choices.";
  }
  if (note.startsWith("User edited matching preferences")) {
    return "Draft from your profile editor: update the editable matching rules.";
  }
  return note;
}

function ProfileRuntimeSettingsControl({
  profile,
  setProfileRuntimeSettings,
  createProfileDraftNote,
  createProfileMatchingPreferencesDraft,
  busy,
}: {
  profile: Profile;
  setProfileRuntimeSettings: (profileId: string, settings: ProfileRuntimeSettings) => void;
  createProfileDraftNote: (profileId: string, note: string) => Promise<void>;
  createProfileMatchingPreferencesDraft: (profileId: string, preferences: string) => Promise<void>;
  busy: boolean;
}) {
  const currentScanWindow = typeof profile.scan_window_hours === "number" ? profile.scan_window_hours : 24;
  const currentItemLimit = typeof profile.semantic_max_messages === "number" ? profile.semantic_max_messages : 20;
  const currentTimezone = profile.timezone || "";
  const currentWorkdays = normalizeWeekdays(profile.workdays);
  const currentWorkStart = profile.work_start || "";
  const currentWorkEnd = profile.work_end || "";
  const currentWorkInterval = typeof profile.work_interval_minutes === "number" ? profile.work_interval_minutes : undefined;
  const currentOffHoursInterval = typeof profile.off_hours_interval_minutes === "number" ? profile.off_hours_interval_minutes : undefined;
  const currentAlertRule = profile.alert_rule || "high_new_or_changed";
  const currentAlertMaxAge = typeof profile.alert_max_age_minutes === "number" ? profile.alert_max_age_minutes : undefined;
  const currentPreferences = profile.matching_profile?.editable_text || "";
  const [scanWindowHours, setScanWindowHours] = useState(String(currentScanWindow));
  const [itemLimit, setItemLimit] = useState(String(currentItemLimit));
  const [timezone, setTimezone] = useState(currentTimezone);
  const [workdays, setWorkdays] = useState<string[]>(currentWorkdays);
  const [workStart, setWorkStart] = useState(currentWorkStart);
  const [workEnd, setWorkEnd] = useState(currentWorkEnd);
  const [workInterval, setWorkInterval] = useState(currentWorkInterval ? String(currentWorkInterval) : "");
  const [offHoursInterval, setOffHoursInterval] = useState(currentOffHoursInterval ? String(currentOffHoursInterval) : "");
  const [alertRule, setAlertRule] = useState(currentAlertRule);
  const [alertMaxAge, setAlertMaxAge] = useState(currentAlertMaxAge ? String(currentAlertMaxAge) : "");
  const [preferenceNote, setPreferenceNote] = useState(currentPreferences);
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    setScanWindowHours(String(currentScanWindow));
    setItemLimit(String(currentItemLimit));
    setTimezone(currentTimezone);
    setWorkdays(currentWorkdays);
    setWorkStart(currentWorkStart);
    setWorkEnd(currentWorkEnd);
    setWorkInterval(currentWorkInterval ? String(currentWorkInterval) : "");
    setOffHoursInterval(currentOffHoursInterval ? String(currentOffHoursInterval) : "");
    setAlertRule(currentAlertRule);
    setAlertMaxAge(currentAlertMaxAge ? String(currentAlertMaxAge) : "");
    if (!editing) {
      setPreferenceNote(currentPreferences);
    }
  }, [
    currentScanWindow,
    currentItemLimit,
    currentTimezone,
    currentWorkdays.join(","),
    currentWorkStart,
    currentWorkEnd,
    currentWorkInterval,
    currentOffHoursInterval,
    currentAlertRule,
    currentAlertMaxAge,
    currentPreferences,
    editing,
  ]);

  const saveState = runtimeSettingsSaveState(
    {
      scan_window_hours: currentScanWindow,
      semantic_max_messages: currentItemLimit,
      timezone: currentTimezone,
      workdays: currentWorkdays,
      work_start: currentWorkStart,
      work_end: currentWorkEnd,
      work_interval_minutes: currentWorkInterval,
      off_hours_interval_minutes: currentOffHoursInterval,
      alert_rule: currentAlertRule,
      alert_max_age_minutes: currentAlertMaxAge,
    },
    {
      scanWindowText: scanWindowHours,
      itemLimitText: itemLimit,
      timezoneText: timezone,
      workdays,
      workStartText: workStart,
      workEndText: workEnd,
      workIntervalText: workInterval,
      offHoursIntervalText: offHoursInterval,
      alertRule,
      alertMaxAgeText: alertMaxAge,
    },
  );
  const normalizedPreference = preferenceNote.trim();
  const canDraftPreferences = Boolean(normalizedPreference) && normalizedPreference !== currentPreferences.trim();

  if (!editing) {
    return (
      <button className="profile-edit-settings text-button" disabled={busy} onClick={() => setEditing(true)} type="button">
        <SlidersHorizontal size={15} />
        <span>Edit profile</span>
      </button>
    );
  }

  return (
    <div className="profile-runtime-settings" aria-label={`Editable profile settings for ${profile.display_name || profileDisplayName(profile.profile_id)}`}>
      <div className="profile-runtime-numbers">
        <label>
          <span className="profile-field-title">
            Hours to check
            <ProfileHelpTip text="How far back each scan reads saved-channel posts." />
          </span>
          <input
            aria-label={`${profile.profile_id} scan window hours`}
            disabled={busy}
            inputMode="numeric"
            max={168}
            min={1}
            onChange={(event) => setScanWindowHours(event.target.value)}
            step={1}
            type="number"
            value={scanWindowHours}
          />
          <small>hours back</small>
        </label>
        <label>
          <span className="profile-field-title">
            Posts to read
            <ProfileHelpTip text="Maximum recent posts Signal Desk ranks for this profile each scan." />
          </span>
          <input
            aria-label={`${profile.profile_id} item limit`}
            disabled={busy}
            inputMode="numeric"
            max={500}
            min={1}
            onChange={(event) => setItemLimit(event.target.value)}
            step={1}
            type="number"
            value={itemLimit}
          />
          <small>per scan</small>
        </label>
      </div>
      <div className="profile-runtime-schedule">
        <label>
          <span className="profile-field-title">
            Timezone
            <ProfileHelpTip text="IANA timezone used for work-hours scheduling." />
          </span>
          <input
            aria-label={`${profile.profile_id} timezone`}
            disabled={busy}
            onChange={(event) => setTimezone(event.target.value)}
            placeholder="Asia/Shanghai"
            value={timezone}
          />
        </label>
        <label>
          <span className="profile-field-title">
            Work starts
            <ProfileHelpTip text="Start of the local work-hours notification window." />
          </span>
          <input
            aria-label={`${profile.profile_id} work start`}
            disabled={busy}
            onChange={(event) => setWorkStart(event.target.value)}
            type="time"
            value={workStart}
          />
        </label>
        <label>
          <span className="profile-field-title">
            Work ends
            <ProfileHelpTip text="End of the local work-hours notification window." />
          </span>
          <input
            aria-label={`${profile.profile_id} work end`}
            disabled={busy}
            onChange={(event) => setWorkEnd(event.target.value)}
            type="time"
            value={workEnd}
          />
        </label>
        <label>
          <span className="profile-field-title">
            Work interval
            <ProfileHelpTip text="Dry-run scheduler cadence during work hours." />
          </span>
          <input
            aria-label={`${profile.profile_id} work interval minutes`}
            disabled={busy}
            inputMode="numeric"
            max={1440}
            min={1}
            onChange={(event) => setWorkInterval(event.target.value)}
            step={1}
            type="number"
            value={workInterval}
          />
          <small>minutes</small>
        </label>
        <label>
          <span className="profile-field-title">
            Quiet interval
            <ProfileHelpTip text="Dry-run scheduler cadence outside work hours." />
          </span>
          <input
            aria-label={`${profile.profile_id} off hours interval minutes`}
            disabled={busy}
            inputMode="numeric"
            max={1440}
            min={1}
            onChange={(event) => setOffHoursInterval(event.target.value)}
            step={1}
            type="number"
            value={offHoursInterval}
          />
          <small>minutes</small>
        </label>
        <label>
          <span className="profile-field-title">
            Alert rule
            <ProfileHelpTip text="Use high-new-only for noisy profiles where changed items should not alert again." />
          </span>
          <select
            aria-label={`${profile.profile_id} alert rule`}
            disabled={busy}
            onChange={(event) => setAlertRule(event.target.value)}
            value={alertRule}
          >
            <option value="high_new_or_changed">High new or changed</option>
            <option value="high_new_only">High new only</option>
          </select>
        </label>
        <label>
          <span className="profile-field-title">
            Alert age
            <ProfileHelpTip text="Maximum age for high-signal items before notifications are skipped." />
          </span>
          <input
            aria-label={`${profile.profile_id} alert max age minutes`}
            disabled={busy}
            inputMode="numeric"
            max={10080}
            min={1}
            onChange={(event) => setAlertMaxAge(event.target.value)}
            step={1}
            type="number"
            value={alertMaxAge}
          />
          <small>minutes</small>
        </label>
      </div>
      <fieldset className="profile-runtime-weekdays">
        <legend className="profile-field-title">
          Workdays
          <ProfileHelpTip text="Days included in this profile's work-hours schedule." />
        </legend>
        <div className="profile-weekday-options">
          {PROFILE_WEEKDAY_OPTIONS.map((day) => (
            <label className="profile-weekday-toggle" key={day.value}>
              <input
                checked={workdays.includes(day.value)}
                disabled={busy}
                onChange={(event) => {
                  if (event.target.checked) {
                    setWorkdays(normalizeWeekdays([...workdays, day.value]));
                  } else {
                    setWorkdays(workdays.filter((value) => value !== day.value));
                  }
                }}
                type="checkbox"
              />
              <span>{day.label}</span>
            </label>
          ))}
        </div>
      </fieldset>
      <label className="profile-preference-note">
        <span className="profile-field-title">
          Matching rules
          <ProfileHelpTip text={currentPreferences
            ? "Edit learned rules here. Signal Desk will preview a draft before the rules affect matching."
            : "Write plain-language rules here. Signal Desk will preview a draft before applying them."}
          />
        </span>
        <textarea
          aria-label={`${profile.profile_id} background and match rules`}
          disabled={busy}
          maxLength={4000}
          onChange={(event) => setPreferenceNote(event.target.value)}
          placeholder={"- Prefer senior remote AI engineering roles\n- Avoid unpaid internships and vague promos"}
          value={preferenceNote}
        />
        {preferenceNote.length > 3600 && <small>{4000 - preferenceNote.length} characters left before the preview limit.</small>}
      </label>
      <div className="profile-runtime-actions">
        <button
          className="profile-save-settings profile-primary-action text-button"
          disabled={busy || !saveState.canSave}
          onClick={() => {
            if (!saveState.canSave) {
              return;
            }
            setProfileRuntimeSettings(profile.profile_id, {
              ...saveState.settings,
            });
            setEditing(false);
          }}
          type="button"
        >
          <Save size={15} />
          <span>Save scan settings</span>
        </button>
        <button
          className="profile-save-settings profile-secondary-action text-button"
          disabled={busy || !canDraftPreferences}
          onClick={() => {
            if (!canDraftPreferences) {
              return;
            }
            void createProfileMatchingPreferencesDraft(profile.profile_id, normalizedPreference).then(() => {
              setEditing(false);
            });
          }}
          title={canDraftPreferences ? "Preview these matching-rule changes" : "Change the matching rules first"}
          type="button"
        >
          <FileDiff size={15} />
          <span>Preview matching changes</span>
        </button>
        <button
          className="profile-save-settings profile-tertiary-action text-button secondary"
          disabled={busy || !normalizedPreference}
          onClick={() => {
            if (!normalizedPreference) {
              return;
            }
            void createProfileDraftNote(profile.profile_id, normalizedPreference).then(() => {
              setEditing(false);
            });
          }}
          title={normalizedPreference ? "Add this as a separate profile note" : "Write a matching note first"}
          type="button"
        >
          <FileDiff size={15} />
          <span>Add as draft note</span>
        </button>
        <button
          className="profile-cancel-settings text-button"
          disabled={busy}
          onClick={() => {
            setScanWindowHours(String(currentScanWindow));
            setItemLimit(String(currentItemLimit));
            setTimezone(currentTimezone);
            setWorkdays(currentWorkdays);
            setWorkStart(currentWorkStart);
            setWorkEnd(currentWorkEnd);
            setWorkInterval(currentWorkInterval ? String(currentWorkInterval) : "");
            setOffHoursInterval(currentOffHoursInterval ? String(currentOffHoursInterval) : "");
            setAlertRule(currentAlertRule);
            setAlertMaxAge(currentAlertMaxAge ? String(currentAlertMaxAge) : "");
            setPreferenceNote(currentPreferences);
            setEditing(false);
          }}
          type="button"
        >
          <span>Cancel</span>
        </button>
      </div>
    </div>
  );
}

function ProfileHelpTip({ text }: { text: string }) {
  return (
    <span className="profile-help-tip" aria-label={text} tabIndex={0}>
      <CircleHelp size={13} aria-hidden="true" />
      <span role="tooltip">{text}</span>
    </span>
  );
}

function ProfileEnabledControl({
  profile,
  setProfileEnabled,
  busy,
}: {
  profile: Profile;
  setProfileEnabled: (profileId: string, enabled: boolean) => void;
  busy: boolean;
}) {
  const nextEnabled = !profile.enabled;
  return (
    <button
      aria-label={`${profile.display_name || profileDisplayName(profile.profile_id)}: ${nextEnabled ? "Resume monitoring" : "Pause monitoring"}`}
      className={`profile-enable-button text-button ${profile.enabled ? "secondary" : ""}`}
      disabled={busy}
      onClick={() => setProfileEnabled(profile.profile_id, nextEnabled)}
      type="button"
    >
      {profile.enabled ? <CirclePause size={15} /> : <CirclePlay size={15} />}
      <span>{profile.enabled ? "Pause" : "Resume"}</span>
    </button>
  );
}

function AlertModeControl({
  profile,
  setAlertMode,
  busy,
}: {
  profile: Profile;
  setAlertMode: (profileId: string, mode: string) => void;
  busy: boolean;
}) {
  const mode = alertMode(profile);
  const modes = [
    { value: "work_hours", label: "Workday", title: "Notify during the workday", icon: <Sun size={14} /> },
    { value: "all_day", label: "Always", title: "Notify any time", icon: <Bell size={14} /> },
    { value: "muted", label: "Off", title: "Do not send notifications", icon: <BellOff size={14} /> },
  ];
  return (
    <div className="mode-controls" aria-label={`${profile.profile_id} alerts`}>
      {modes.map((item) => (
        <button
          className={mode === item.value ? "mode-button active" : "mode-button"}
          key={item.value}
          type="button"
          title={item.title}
          disabled={busy || !profile.enabled}
          onClick={() => setAlertMode(profile.profile_id, item.value)}
        >
          {item.icon}
          <span>{item.label}</span>
        </button>
      ))}
    </div>
  );
}

function profileScanWindowLabel(profile: Profile) {
  const formatted = formatScanWindow(profile.scan_window_hours).toLowerCase();
  return formatted === "window n/a" ? "Scan history" : formatted.replace(" scan", " history");
}

function profileItemLimitLabel(profile: Profile) {
  if (typeof profile.semantic_max_messages !== "number") {
    return "Item limit";
  }
  return `${profile.semantic_max_messages} messages`;
}

function profileTopicLabel(profile: Profile) {
  return profile.source_topics?.[0] ? titleCaseLabel(profile.source_topics[0]) : "All topics";
}

function profileNotificationLabel(profile: Profile) {
  if (typeof profile.delivery_target_count !== "number") {
    return "Notifications";
  }
  return profile.delivery_target_count === 1 ? "1 notification" : `${profile.delivery_target_count} notifications`;
}

const PROFILE_WEEKDAY_OPTIONS = [
  { value: "mon", label: "Mon" },
  { value: "tue", label: "Tue" },
  { value: "wed", label: "Wed" },
  { value: "thu", label: "Thu" },
  { value: "fri", label: "Fri" },
  { value: "sat", label: "Sat" },
  { value: "sun", label: "Sun" },
];

const PROFILE_WEEKDAY_SET = new Set(PROFILE_WEEKDAY_OPTIONS.map((day) => day.value));
const PROFILE_ALERT_RULES = new Set(["high_new_or_changed", "high_new_only"]);

type RuntimeSettingsDraft = {
  scanWindowText: string;
  itemLimitText: string;
  timezoneText: string;
  workdays: string[];
  workStartText: string;
  workEndText: string;
  workIntervalText: string;
  offHoursIntervalText: string;
  alertRule: string;
  alertMaxAgeText: string;
};

export function runtimeSettingsSaveState(current: ProfileRuntimeSettings, draft: RuntimeSettingsDraft) {
  const settings: ProfileRuntimeSettings = {};
  const scanValue = parseIntegerField(draft.scanWindowText, 1, 168);
  const itemValue = parseIntegerField(draft.itemLimitText, 1, 500);
  const workIntervalValue = parseOptionalIntegerField(draft.workIntervalText, current.work_interval_minutes, 1, 1440);
  const offHoursIntervalValue = parseOptionalIntegerField(draft.offHoursIntervalText, current.off_hours_interval_minutes, 1, 1440);
  const alertMaxAgeValue = parseOptionalIntegerField(draft.alertMaxAgeText, current.alert_max_age_minutes, 1, 10080);
  const timezone = draft.timezoneText.trim();
  const workStart = draft.workStartText.trim();
  const workEnd = draft.workEndText.trim();
  const currentWorkdays = normalizeWeekdays(current.workdays);
  const draftWorkdays = normalizeWeekdays(draft.workdays);
  const hasWorkdayChange = currentWorkdays.join(",") !== draftWorkdays.join(",");
  const timezoneValid = isOptionalTimezoneValid(timezone, current.timezone);
  const workStartValid = isOptionalTimeValid(workStart, current.work_start);
  const workEndValid = isOptionalTimeValid(workEnd, current.work_end);
  const workdaysValid = draftWorkdays.length > 0 || currentWorkdays.length === 0;
  const alertRule = PROFILE_ALERT_RULES.has(draft.alertRule) ? draft.alertRule : "";
  const valid =
    scanValue.valid &&
    itemValue.valid &&
    workIntervalValue.valid &&
    offHoursIntervalValue.valid &&
    alertMaxAgeValue.valid &&
    timezoneValid &&
    workStartValid &&
    workEndValid &&
    workdaysValid &&
    Boolean(alertRule);
  if (scanValue.valid && scanValue.value !== current.scan_window_hours) {
    settings.scan_window_hours = scanValue.value;
  }
  if (itemValue.valid && itemValue.value !== current.semantic_max_messages) {
    settings.semantic_max_messages = itemValue.value;
  }
  if (timezone && timezone !== (current.timezone || "")) {
    settings.timezone = timezone;
  }
  if (hasWorkdayChange && draftWorkdays.length > 0) {
    settings.workdays = draftWorkdays;
  }
  if (workStart && workStart !== (current.work_start || "")) {
    settings.work_start = workStart;
  }
  if (workEnd && workEnd !== (current.work_end || "")) {
    settings.work_end = workEnd;
  }
  if (workIntervalValue.valid && workIntervalValue.value !== undefined && workIntervalValue.value !== current.work_interval_minutes) {
    settings.work_interval_minutes = workIntervalValue.value;
  }
  if (offHoursIntervalValue.valid && offHoursIntervalValue.value !== undefined && offHoursIntervalValue.value !== current.off_hours_interval_minutes) {
    settings.off_hours_interval_minutes = offHoursIntervalValue.value;
  }
  if (alertRule && alertRule !== (current.alert_rule || "high_new_or_changed")) {
    settings.alert_rule = alertRule;
  }
  if (alertMaxAgeValue.valid && alertMaxAgeValue.value !== undefined && alertMaxAgeValue.value !== current.alert_max_age_minutes) {
    settings.alert_max_age_minutes = alertMaxAgeValue.value;
  }
  return {
    canSave: valid && Object.keys(settings).length > 0,
    settings,
  };
}

function parseIntegerField(text: string, min: number, max: number) {
  const value = Number(text);
  const valid = Number.isInteger(value) && value >= min && value <= max;
  return { valid, value };
}

function parseOptionalIntegerField(text: string, current: number | undefined, min: number, max: number) {
  const trimmed = text.trim();
  if (!trimmed && current === undefined) {
    return { valid: true, value: undefined };
  }
  const value = Number(trimmed);
  const valid = Number.isInteger(value) && value >= min && value <= max;
  return { valid, value };
}

function isOptionalTimezoneValid(value: string, current: string | undefined) {
  if (!value && !current) {
    return true;
  }
  return /^[A-Za-z0-9_+\-]+(?:\/[A-Za-z0-9_+\-]+)*$/.test(value) && !value.includes("..") && !value.includes("//");
}

function isOptionalTimeValid(value: string, current: string | undefined) {
  if (!value && !current) {
    return true;
  }
  if (!/^\d{2}:\d{2}$/.test(value)) {
    return false;
  }
  const [hourText, minuteText] = value.split(":");
  const hour = Number(hourText);
  const minute = Number(minuteText);
  return Number.isInteger(hour) && Number.isInteger(minute) && hour >= 0 && hour <= 23 && minute >= 0 && minute <= 59;
}

function normalizeWeekdays(value: unknown) {
  if (!Array.isArray(value)) {
    return [];
  }
  const normalized: string[] = [];
  value.forEach((item) => {
    if (typeof item !== "string") {
      return;
    }
    const day = item.trim().toLowerCase().slice(0, 3);
    if (PROFILE_WEEKDAY_SET.has(day) && !normalized.includes(day)) {
      normalized.push(day);
    }
  });
  return normalized;
}
