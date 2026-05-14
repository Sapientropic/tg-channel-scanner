import { FileDiff, LocateFixed, Save } from "lucide-react";
import type { Dispatch, SetStateAction } from "react";

import type { ProfileRuntimeSettings } from "../../domain/types";
import {
  PROFILE_WEEKDAY_OPTIONS,
  detectedBrowserTimezone,
  normalizeWeekdays,
  timezoneOptions,
} from "./runtime-settings-model";
import { ProfileHelpTip } from "./profile-help-tip";

export function RuntimeScanScopeFields({
  profileId,
  busy,
  scanWindowHours,
  setScanWindowHours,
  itemLimit,
  setItemLimit,
}: {
  profileId: string;
  busy: boolean;
  scanWindowHours: string;
  setScanWindowHours: (value: string) => void;
  itemLimit: string;
  setItemLimit: (value: string) => void;
}) {
  return (
    <fieldset className="profile-runtime-group profile-runtime-scope">
      <legend>
        Scan scope
        <ProfileHelpTip text="How much saved-channel history this profile reads each time it scans." />
      </legend>
      <p>Use smaller numbers for fast checks; increase them only when important posts are missed.</p>
      <div className="profile-field-grid two">
        <label>
          <span className="profile-field-title">Hours to check</span>
          <input
            aria-label={`${profileId} scan window hours`}
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
          <span className="profile-field-title">Posts to read</span>
          <input
            aria-label={`${profileId} item limit`}
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
    </fieldset>
  );
}

export function RuntimeWorkHoursFields({
  profileId,
  busy,
  timezone,
  setTimezone,
  workStart,
  setWorkStart,
  workEnd,
  setWorkEnd,
  workdays,
  setWorkdays,
}: {
  profileId: string;
  busy: boolean;
  timezone: string;
  setTimezone: (value: string) => void;
  workStart: string;
  setWorkStart: (value: string) => void;
  workEnd: string;
  setWorkEnd: (value: string) => void;
  workdays: string[];
  setWorkdays: Dispatch<SetStateAction<string[]>>;
}) {
  const detectedTimezone = detectedBrowserTimezone();
  const options = timezoneOptions(timezone, detectedTimezone);
  return (
    <fieldset className="profile-runtime-group profile-runtime-work-hours">
      <legend>
        Work hours
        <ProfileHelpTip text="The local time window used when this profile is set to workday notifications." />
      </legend>
      <p>These settings decide when live alerts are allowed; they do not change what gets scanned.</p>
      <div className="profile-field-grid three">
        <label>
          <span className="profile-field-title">Timezone</span>
          <div className="profile-timezone-control">
            <input
              aria-label={`${profileId} timezone`}
              disabled={busy}
              list={`${profileId}-timezone-options`}
              onChange={(event) => setTimezone(event.target.value)}
              placeholder={detectedTimezone || "Asia/Shanghai"}
              value={timezone}
            />
            <datalist id={`${profileId}-timezone-options`}>
              {options.map((option) => (
                <option key={option} value={option} />
              ))}
            </datalist>
            {detectedTimezone && (
              <button
                aria-label={`Use detected timezone ${detectedTimezone}`}
                className="profile-detect-timezone"
                disabled={busy}
                onClick={() => setTimezone(detectedTimezone)}
                title={`Use detected timezone: ${detectedTimezone}`}
                type="button"
              >
                <LocateFixed size={14} />
                <span>Use detected</span>
              </button>
            )}
          </div>
        </label>
        <label>
          <span className="profile-field-title">Work starts</span>
          <input
            aria-label={`${profileId} work start`}
            disabled={busy}
            onChange={(event) => setWorkStart(event.target.value)}
            type="time"
            value={workStart}
          />
        </label>
        <label>
          <span className="profile-field-title">Work ends</span>
          <input
            aria-label={`${profileId} work end`}
            disabled={busy}
            onChange={(event) => setWorkEnd(event.target.value)}
            type="time"
            value={workEnd}
          />
        </label>
      </div>
      <div className="profile-weekday-block">
        <span className="profile-field-title">
          Workdays
          <ProfileHelpTip text="Days included in this profile's work-hours schedule." />
        </span>
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
        {!workdays.length && <small className="profile-workdays-default">No days selected means every day.</small>}
      </div>
    </fieldset>
  );
}

export function RuntimeAlertFields({
  profileId,
  busy,
  workInterval,
  setWorkInterval,
  offHoursInterval,
  setOffHoursInterval,
  alertRule,
  setAlertRule,
  alertMaxAge,
  setAlertMaxAge,
}: {
  profileId: string;
  busy: boolean;
  workInterval: string;
  setWorkInterval: (value: string) => void;
  offHoursInterval: string;
  setOffHoursInterval: (value: string) => void;
  alertRule: string;
  setAlertRule: (value: string) => void;
  alertMaxAge: string;
  setAlertMaxAge: (value: string) => void;
}) {
  return (
    <fieldset className="profile-runtime-group profile-runtime-alerts">
      <legend>
        Check frequency and alerts
        <ProfileHelpTip text="These settings control how often this profile checks sources and which fresh cards can notify you." />
      </legend>
      <p>Leave a field blank for the default. Use shorter intervals only for profiles that need fast action.</p>
      <div className="profile-field-grid four">
        <label>
          <span className="profile-field-title">Work hours check every</span>
          <input
            aria-label={`${profileId} work interval minutes`}
            disabled={busy}
            inputMode="numeric"
            max={1440}
            min={1}
            onChange={(event) => setWorkInterval(event.target.value)}
            step={1}
            type="number"
            value={workInterval}
          />
          <small>minutes during work hours</small>
        </label>
        <label>
          <span className="profile-field-title">After hours check every</span>
          <input
            aria-label={`${profileId} off hours interval minutes`}
            disabled={busy}
            inputMode="numeric"
            max={1440}
            min={1}
            onChange={(event) => setOffHoursInterval(event.target.value)}
            step={1}
            type="number"
            value={offHoursInterval}
          />
          <small>minutes outside work hours</small>
        </label>
        <label>
          <span className="profile-field-title">Notify when</span>
          <select
            aria-label={`${profileId} alert rule`}
            disabled={busy}
            onChange={(event) => setAlertRule(event.target.value)}
            value={alertRule}
          >
            <option value="high_new_or_changed">High new or changed</option>
            <option value="high_new_only">High new only</option>
          </select>
        </label>
        <label>
          <span className="profile-field-title">Do not alert items older than</span>
          <input
            aria-label={`${profileId} alert max age minutes`}
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
    </fieldset>
  );
}

export function RuntimeMatchingRulesField({
  profileId,
  busy,
  currentPreferences,
  preferenceNote,
  setPreferenceNote,
}: {
  profileId: string;
  busy: boolean;
  currentPreferences: string;
  preferenceNote: string;
  setPreferenceNote: (value: string) => void;
}) {
  return (
    <div className="profile-runtime-group profile-runtime-matching">
      <label className="profile-preference-note">
        <span className="profile-field-title">
          Matching rules
          <ProfileHelpTip text={currentPreferences
            ? "Edit learned rules here. Signal Desk will preview a draft before the rules affect matching."
            : "Write plain-language rules here. Signal Desk will preview a draft before applying them."}
          />
        </span>
        <textarea
          aria-label={`${profileId} background and match rules`}
          disabled={busy}
          maxLength={4000}
          onChange={(event) => setPreferenceNote(event.target.value)}
          placeholder={"- Prefer senior remote AI engineering roles\n- Avoid unpaid internships and vague promos"}
          value={preferenceNote}
        />
        {preferenceNote.length > 3600 && <small>{4000 - preferenceNote.length} characters left before the preview limit.</small>}
      </label>
    </div>
  );
}

export function RuntimeSettingsActions({
  profileId,
  busy,
  canSaveSettings,
  settings,
  canDraftPreferences,
  normalizedPreference,
  setProfileRuntimeSettings,
  createProfileDraftNote,
  createProfileMatchingPreferencesDraft,
  closeEditor,
  resetDraft,
}: {
  profileId: string;
  busy: boolean;
  canSaveSettings: boolean;
  settings: ProfileRuntimeSettings;
  canDraftPreferences: boolean;
  normalizedPreference: string;
  setProfileRuntimeSettings: (profileId: string, settings: ProfileRuntimeSettings) => void;
  createProfileDraftNote: (profileId: string, note: string) => Promise<void>;
  createProfileMatchingPreferencesDraft: (profileId: string, preferences: string) => Promise<void>;
  closeEditor: () => void;
  resetDraft: () => void;
}) {
  return (
    <div className="profile-runtime-actions">
      <button
        className="profile-save-settings profile-primary-action text-button"
        disabled={busy || !canSaveSettings}
        onClick={() => {
          if (!canSaveSettings) {
            return;
          }
          setProfileRuntimeSettings(profileId, {
            ...settings,
          });
          closeEditor();
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
          void createProfileMatchingPreferencesDraft(profileId, normalizedPreference).then(closeEditor);
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
          void createProfileDraftNote(profileId, normalizedPreference).then(closeEditor);
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
          resetDraft();
          closeEditor();
        }}
        type="button"
      >
        <span>Cancel</span>
      </button>
    </div>
  );
}
