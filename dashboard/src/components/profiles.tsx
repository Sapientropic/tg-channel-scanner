import { useEffect, useState } from "react";
import { Bell, BellOff, Check, FileDiff, Pause, Play, RefreshCw, Save, SlidersHorizontal, Sun, UserRoundCog, X } from "lucide-react";

import { InlineEmpty, PanelHeader } from "./common";
import { alertMode, diffStats, toneClass } from "../domain/display";
import { formatDate, formatScanWindow, profileDisplayName, titleCaseLabel } from "../domain/format";
import type { Profile, ProfilePatch } from "../domain/types";

export function ProfilesView({
  profiles,
  patches,
  applyPatch,
  revertPatch,
  setAlertMode,
  setProfileEnabled,
  setProfileRuntimeSettings,
  busy,
}: {
  profiles: Profile[];
  patches: ProfilePatch[];
  applyPatch: (patchId: string) => void;
  revertPatch: (patchId: string) => void;
  setAlertMode: (profileId: string, mode: string) => void;
  setProfileEnabled: (profileId: string, enabled: boolean) => void;
  setProfileRuntimeSettings: (profileId: string, settings: { scan_window_hours?: number; semantic_max_messages?: number }) => void;
  busy: boolean;
}) {
  return (
    <section className="split-section">
      <div className="plain-panel">
        <PanelHeader icon={<UserRoundCog size={18} />} title="Profiles" count={profiles.length} />
        {profiles.length ? (
          <div className="table-list">
            {profiles.map((profile) => (
              <div className={`table-row profile-row ${profile.enabled ? "" : "paused"}`} key={profile.profile_id}>
                <div className="profile-primary">
                  <strong>{profile.display_name || profileDisplayName(profile.profile_id)}</strong>
                  <span className={profile.enabled ? "status enabled" : "status disabled"}>
                    {profile.enabled ? "Monitoring" : "Paused"}
                  </span>
                </div>
                <div className="profile-rhythm" aria-label={`Scan settings for ${profile.display_name || profileDisplayName(profile.profile_id)}`}>
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
                    <span className="profile-control-label">Alerts</span>
                    <AlertModeControl profile={profile} setAlertMode={setAlertMode} busy={busy} />
                    {!profile.enabled && <span className="profile-paused-note">Resume monitoring to adjust alerts.</span>}
                  </div>
                </div>
                <ProfileRuntimeSettingsControl
                  profile={profile}
                  setProfileRuntimeSettings={setProfileRuntimeSettings}
                  busy={busy}
                />
              </div>
            ))}
          </div>
        ) : (
          <InlineEmpty title="No profiles registered" />
        )}
      </div>
      <div className="plain-panel">
        <PanelHeader icon={<FileDiff size={18} />} title="Profile Diffs" count={patches.length} />
        {patches.length ? (
          <div className="patch-list">
            {patches.map((patch) => {
              const stats = diffStats(patch.diff_text);
              return (
                <article className="review-card patch-card" key={patch.patch_id}>
                  <div className="card-main">
                    <div className="card-title-row">
                      <h3>{patch.card_title || patch.profile_id}</h3>
                      <span className={`status ${toneClass(patch.status)}`}>{patch.status}</span>
                    </div>
                    <div className="patch-context-row">
                      <span>{profileDisplayName(patch.profile_id)}</span>
                      <code title={patch.profile_display_path || "Profile path unavailable"}>
                        {patch.profile_display_path || "Profile path unavailable"}
                      </code>
                      <span>{formatDate(patch.created_at)}</span>
                      {patch.applied_at && <span>applied {formatDate(patch.applied_at)}</span>}
                      <span className="patch-diff-stat">+{stats.added} / -{stats.removed}</span>
                      {patch.base_profile_short_hash && <span>base {patch.base_profile_short_hash}</span>}
                    </div>
                    {patch.apply_readiness && (
                      <div className={`patch-readiness ${toneClass(patch.apply_readiness.status || "unknown")}`}>
                        <strong>{patch.apply_readiness.label || "Readiness check"}</strong>
                        {patch.apply_readiness.detail && <span>{patch.apply_readiness.detail}</span>}
                      </div>
                    )}
                    <p className="note-line">{patch.note || "Follow-up preference draft"}</p>
                    <details className="patch-diff-details">
                      <summary>
                        <FileDiff size={14} />
                        <span>View patch</span>
                      </summary>
                      <pre>{patch.diff_text || "No diff body recorded."}</pre>
                    </details>
                    <div className="patch-actions">
                      {patch.status === "pending" && (
                        <button
                          className="text-button"
                          type="button"
                          onClick={() => applyPatch(patch.patch_id)}
                          disabled={busy}
                        >
                          <Check size={15} />
                          <span>Apply</span>
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
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <InlineEmpty title="No pending profile diffs" />
        )}
      </div>
    </section>
  );
}

function ProfileRuntimeSettingsControl({
  profile,
  setProfileRuntimeSettings,
  busy,
}: {
  profile: Profile;
  setProfileRuntimeSettings: (profileId: string, settings: { scan_window_hours?: number; semantic_max_messages?: number }) => void;
  busy: boolean;
}) {
  const currentScanWindow = typeof profile.scan_window_hours === "number" ? profile.scan_window_hours : 24;
  const currentItemLimit = typeof profile.semantic_max_messages === "number" ? profile.semantic_max_messages : 20;
  const [scanWindowHours, setScanWindowHours] = useState(String(currentScanWindow));
  const [itemLimit, setItemLimit] = useState(String(currentItemLimit));
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    setScanWindowHours(String(currentScanWindow));
    setItemLimit(String(currentItemLimit));
  }, [currentScanWindow, currentItemLimit]);

  const saveState = runtimeSettingsSaveState(currentScanWindow, currentItemLimit, scanWindowHours, itemLimit);

  if (!editing) {
    return (
      <button className="profile-edit-settings text-button" disabled={busy} onClick={() => setEditing(true)} type="button">
        <SlidersHorizontal size={15} />
        <span>Scan settings</span>
      </button>
    );
  }

  return (
    <div className="profile-runtime-settings" aria-label={`Editable scan settings for ${profile.display_name || profileDisplayName(profile.profile_id)}`}>
      <label>
        <span>Scan history</span>
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
        <small>hours</small>
      </label>
      <label>
        <span>Messages</span>
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
      <div className="profile-runtime-actions">
        <button
          className="profile-save-settings text-button"
          disabled={busy || !saveState.canSave}
          onClick={() => {
            if (!saveState.canSave) {
              return;
            }
            setProfileRuntimeSettings(profile.profile_id, {
              scan_window_hours: saveState.scan_window_hours,
              semantic_max_messages: saveState.semantic_max_messages,
            });
            setEditing(false);
          }}
          type="button"
        >
          <Save size={15} />
          <span>Save</span>
        </button>
        <button
          className="profile-cancel-settings text-button"
          disabled={busy}
          onClick={() => {
            setScanWindowHours(String(currentScanWindow));
            setItemLimit(String(currentItemLimit));
            setEditing(false);
          }}
          type="button"
        >
          <X size={15} />
          <span>Cancel</span>
        </button>
      </div>
    </div>
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
      {profile.enabled ? <Pause size={15} /> : <Play size={15} />}
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
    { value: "work_hours", label: "Day", icon: <Sun size={14} /> },
    { value: "all_day", label: "All", icon: <Bell size={14} /> },
    { value: "muted", label: "Mute", icon: <BellOff size={14} /> },
  ];
  return (
    <div className="mode-controls" aria-label={`${profile.profile_id} alerts`}>
      {modes.map((item) => (
        <button
          className={mode === item.value ? "mode-button active" : "mode-button"}
          key={item.value}
          type="button"
          title={item.label}
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

export function runtimeSettingsSaveState(
  currentScanWindow: number,
  currentItemLimit: number,
  scanWindowText: string,
  itemLimitText: string,
) {
  const scanValue = Number(scanWindowText);
  const itemValue = Number(itemLimitText);
  const validScan = Number.isInteger(scanValue) && scanValue >= 1 && scanValue <= 168;
  const validItems = Number.isInteger(itemValue) && itemValue >= 1 && itemValue <= 500;
  return {
    canSave: validScan && validItems && (scanValue !== currentScanWindow || itemValue !== currentItemLimit),
    scan_window_hours: scanValue,
    semantic_max_messages: itemValue,
  };
}
