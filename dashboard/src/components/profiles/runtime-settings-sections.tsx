import { Bell, CalendarDays, FileDiff, Gauge, LocateFixed, Save } from "lucide-react";
import type { CSSProperties, Dispatch, SetStateAction } from "react";

import type { ProfileRuntimeSettings } from "../../domain/types";
import {
  PROFILE_WEEKDAY_OPTIONS,
  detectedBrowserTimezone,
  normalizeWeekdays,
  timezoneOptions,
} from "./runtime-settings-model";
import { ProfileHelpTip } from "./profile-help-tip";

const SCAN_PRESETS = [
  { id: "fast", label: "Fast", hours: "2", posts: "40", detail: "Fresh lead lane" },
  { id: "daily", label: "Daily", hours: "12", posts: "120", detail: "Catch-up pass" },
  { id: "deep", label: "Deep", hours: "24", posts: "200", detail: "Full-day review" },
] as const;

const TIME_PRESETS = [
  { id: "anytime", label: "Any time", start: "", end: "", detail: "No alert window" },
  { id: "workday", label: "Workday", start: "09:00", end: "18:00", detail: "Daytime checks" },
  { id: "evening", label: "Evening", start: "18:00", end: "23:00", detail: "After-work sweep" },
] as const;

const WEEKDAY_VALUES = ["mon", "tue", "wed", "thu", "fri"];

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
  const selectedPreset = SCAN_PRESETS.find((preset) => preset.hours === scanWindowHours && preset.posts === itemLimit)?.id || "custom";
  const currentLabel = `${scanWindowHours || "-"}h / ${itemLimit || "-"} posts`;
  return (
    <fieldset className="profile-runtime-group profile-runtime-scope profile-visual-control">
      <legend>
        <Gauge size={15} />
        Scan
        <ProfileHelpTip text="How much saved-channel history this profile reads each time it scans." />
      </legend>
      <div className="profile-visual-readout">
        <span>Current</span>
        <strong>{currentLabel}</strong>
        <div className="profile-scan-meter" aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
          <span />
        </div>
      </div>
      <div className="profile-preset-grid" aria-label={`${profileId} scan presets`}>
        {SCAN_PRESETS.map((preset) => (
          <button
            aria-pressed={selectedPreset === preset.id}
            className="profile-preset-card"
            data-selected={selectedPreset === preset.id ? "true" : "false"}
            disabled={busy}
            key={preset.id}
            onClick={() => {
              setScanWindowHours(preset.hours);
              setItemLimit(preset.posts);
            }}
            type="button"
          >
            <strong>{preset.label}</strong>
            <span>
              {preset.hours}h / {preset.posts}
            </span>
            <small>{preset.detail}</small>
          </button>
        ))}
      </div>
      <details className="profile-advanced-panel">
        <summary>Custom scan numbers</summary>
        <div className="profile-field-grid two">
          <label>
            <span className="profile-field-title">History window</span>
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
      </details>
    </fieldset>
  );
}

export function RuntimeNotifyFields({
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
  timezone: string;
  setTimezone: (value: string) => void;
  workStart: string;
  setWorkStart: (value: string) => void;
  workEnd: string;
  setWorkEnd: (value: string) => void;
  workdays: string[];
  setWorkdays: Dispatch<SetStateAction<string[]>>;
  workInterval: string;
  setWorkInterval: (value: string) => void;
  offHoursInterval: string;
  setOffHoursInterval: (value: string) => void;
  alertRule: string;
  setAlertRule: (value: string) => void;
  alertMaxAge: string;
  setAlertMaxAge: (value: string) => void;
}) {
  const detectedTimezone = detectedBrowserTimezone();
  const options = timezoneOptions(timezone, detectedTimezone);
  const selectedTimePreset = TIME_PRESETS.find((preset) => preset.start === workStart && preset.end === workEnd)?.id || "custom";
  const selectedDayPreset = workdays.length === 0 ? "everyday" : sameWeekdays(workdays, WEEKDAY_VALUES) ? "weekdays" : "custom";
  const timeWindowLabel = workStart || workEnd ? `${workStart || "--:--"}-${workEnd || "--:--"}` : "All day";
  const dayLabel = selectedDayPreset === "everyday" ? "Every day" : selectedDayPreset === "weekdays" ? "Mon-Fri" : `${workdays.length} custom days`;
  return (
    <fieldset className="profile-runtime-group profile-runtime-notify profile-visual-control">
      <legend>
        <Bell size={15} />
        Notify
        <ProfileHelpTip text="Choose when this profile may interrupt you and which high-signal changes are worth an alert." />
      </legend>

      <div className="profile-notify-map">
        <div className="profile-time-window-card">
          <div className="profile-visual-readout">
            <span>Alert window</span>
            <strong>{timeWindowLabel}</strong>
            <small>
              {dayLabel} · {timezone || detectedTimezone || "Local timezone"}
            </small>
          </div>
          <div className="profile-time-rail" style={timeRailStyle(workStart, workEnd)} aria-hidden="true">
            <span className="profile-time-tick">00</span>
            <span className="profile-time-tick">06</span>
            <span className="profile-time-tick">12</span>
            <span className="profile-time-tick">18</span>
            <span className="profile-time-tick">24</span>
          </div>
        </div>

        <div className="profile-preset-grid profile-time-presets" aria-label={`${profileId} alert window presets`}>
          {TIME_PRESETS.map((preset) => (
            <button
              aria-pressed={selectedTimePreset === preset.id}
              className="profile-preset-card"
              data-selected={selectedTimePreset === preset.id ? "true" : "false"}
              disabled={busy}
              key={preset.id}
              onClick={() => {
                setWorkStart(preset.start);
                setWorkEnd(preset.end);
              }}
              type="button"
            >
              <strong>{preset.label}</strong>
              <span>{preset.start && preset.end ? `${preset.start}-${preset.end}` : "Open window"}</span>
              <small>{preset.detail}</small>
            </button>
          ))}
        </div>
      </div>

      <div className="profile-day-board">
        <span className="profile-field-title">
          <CalendarDays size={14} />
          Days
        </span>
        <div className="profile-chip-row" aria-label={`${profileId} day presets`}>
          <button
            aria-pressed={selectedDayPreset === "everyday"}
            className="profile-chip-button"
            disabled={busy}
            onClick={() => setWorkdays([])}
            type="button"
          >
            Every day
          </button>
          <button
            aria-pressed={selectedDayPreset === "weekdays"}
            className="profile-chip-button"
            disabled={busy}
            onClick={() => setWorkdays([...WEEKDAY_VALUES])}
            type="button"
          >
            Mon-Fri
          </button>
        </div>
        <div className="profile-weekday-options">
          {PROFILE_WEEKDAY_OPTIONS.map((day) => (
            <button
              aria-pressed={workdays.length === 0 || workdays.includes(day.value)}
              className="profile-weekday-toggle"
              data-selected={workdays.length === 0 || workdays.includes(day.value) ? "true" : "false"}
              disabled={busy}
              key={day.value}
              onClick={() => {
                if (workdays.length === 0) {
                  setWorkdays(PROFILE_WEEKDAY_OPTIONS.map((option) => option.value).filter((value) => value !== day.value));
                } else if (workdays.includes(day.value)) {
                  setWorkdays(workdays.filter((value) => value !== day.value));
                } else {
                  setWorkdays(normalizeWeekdays([...workdays, day.value]));
                }
              }}
              type="button"
            >
              {day.label}
            </button>
          ))}
        </div>
      </div>

      <div className="profile-alert-choice-grid" aria-label={`${profileId} alert rule`}>
        <button
          aria-pressed={alertRule === "high_new_or_changed"}
          className="profile-preset-card"
          data-selected={alertRule === "high_new_or_changed" ? "true" : "false"}
          disabled={busy}
          onClick={() => setAlertRule("high_new_or_changed")}
          type="button"
        >
          <strong>New + changed</strong>
          <span>Alert on fresh high cards and updates</span>
        </button>
        <button
          aria-pressed={alertRule === "high_new_only"}
          className="profile-preset-card"
          data-selected={alertRule === "high_new_only" ? "true" : "false"}
          disabled={busy}
          onClick={() => setAlertRule("high_new_only")}
          type="button"
        >
          <strong>New only</strong>
          <span>Ignore changes to older cards</span>
        </button>
      </div>

      <details className="profile-advanced-panel">
        <summary>Advanced alert timing</summary>
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
          <label>
            <span className="profile-field-title">Workday interval</span>
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
            <span className="profile-field-title">After-hours interval</span>
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
            <span className="profile-field-title">Alert age limit</span>
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
      </details>
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
  const ruleLines = matchingRuleLines(preferenceNote);
  const visibleLines = ruleLines.slice(0, 4);
  const hiddenCount = Math.max(0, ruleLines.length - visibleLines.length);
  const ruleCount = `${ruleLines.length} rule${ruleLines.length === 1 ? "" : "s"}`;
  return (
    <div className="profile-runtime-group profile-runtime-matching profile-visual-control">
      <div className="profile-rules-head">
        <span className="profile-field-title">
          <FileDiff size={15} />
          Rules
          <ProfileHelpTip
            text={
              currentPreferences
                ? "Edit learned rules here. Signal Desk will preview a draft before the rules affect matching."
                : "Write plain-language rules here. Signal Desk will preview a draft before applying them."
            }
          />
        </span>
        <strong>{ruleLines.length ? ruleCount : "No rules yet"}</strong>
      </div>
      <div className="profile-rule-paper" aria-label={`${profileId} matching rules preview`}>
        {visibleLines.length ? (
          <>
            {visibleLines.map((line, index) => (
              <p key={`${index}-${line}`}>{line.replace(/^-+\s*/, "")}</p>
            ))}
            {hiddenCount > 0 && <small>{hiddenCount} more hidden</small>}
          </>
        ) : (
          <p>No matching rules yet.</p>
        )}
      </div>
      <details className="profile-advanced-panel profile-rules-editor">
        <summary>Edit rules</summary>
        <label className="profile-preference-note">
          <span className="profile-field-title">Plain-language matching rules</span>
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
      </details>
    </div>
  );
}

function sameWeekdays(current: string[], target: string[]) {
  const normalizedCurrent = normalizeWeekdays(current);
  return normalizedCurrent.length === target.length && normalizedCurrent.every((value, index) => value === target[index]);
}

function timeRailStyle(workStart: string, workEnd: string): CSSProperties {
  const start = timeToPercent(workStart);
  const end = timeToPercent(workEnd);
  if (start === null || end === null || end <= start) {
    return { "--window-start": "0%", "--window-end": "100%" } as CSSProperties;
  }
  return { "--window-start": `${start}%`, "--window-end": `${end}%` } as CSSProperties;
}

function timeToPercent(value: string) {
  const match = /^(\d{2}):(\d{2})$/.exec(value);
  if (!match) {
    return null;
  }
  const hours = Number(match[1]);
  const minutes = Number(match[2]);
  if (hours > 23 || minutes > 59) {
    return null;
  }
  return ((hours * 60 + minutes) / 1440) * 100;
}

function matchingRuleLines(value: string) {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
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
        aria-label="Save scan settings"
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
        title="Save scan settings"
        type="button"
      >
        <Save size={15} />
        <span>Save</span>
      </button>
      <button
        className="profile-save-settings profile-secondary-action text-button"
        aria-label="Preview matching changes"
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
        <span>Preview</span>
      </button>
      <button
        className="profile-save-settings profile-tertiary-action text-button secondary"
        aria-label="Add matching rules as a draft note"
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
        <span>Draft note</span>
      </button>
      <button
        className="profile-cancel-settings text-button"
        aria-label="Cancel profile settings edit"
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
