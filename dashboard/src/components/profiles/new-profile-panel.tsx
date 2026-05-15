import { Check, FileUp, Plus, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { InlineEmpty } from "../common";
import type { ProfileCreatePreview, ProfileCreateResult, ProfileTemplate, ProfileTemplateCatalog } from "../../domain/types";

const PROFILE_STARTERS = [
  {
    id: "jobs",
    title: "Developer jobs",
    audience: "Developers",
    default_topic: "jobs",
    brief:
      "Watch for paid senior remote frontend, full-stack, TypeScript, React, agent, or Telegram Mini Apps opportunities. Prefer clear budget, contact path, and work format. Avoid unpaid internships, vague promos, and on-site-only roles.",
    questions: [
      "What must be true before a lead is worth acting on?",
      "Which roles, stacks, locations, or work formats should never match?",
      "Give one recent good match and one wrong match if you have them.",
    ],
  },
  {
    id: "airdrops",
    title: "Crypto opportunities",
    audience: "Crypto users",
    default_topic: "airdrops",
    brief:
      "Watch for actionable crypto, TON, airdrop, grant, bounty, and builder opportunities. Prefer credible teams, clear eligibility, timelines, and next steps. Avoid pure price chatter, vague alpha calls, and risky wallet-draining prompts.",
    questions: ["Which ecosystems are in scope?", "What risk signals should always block a match?"],
  },
  {
    id: "competitor-monitoring",
    title: "Competitor signals",
    audience: "Operators",
    default_topic: "competitor-monitoring",
    brief:
      "Watch for competitor launches, pricing changes, hiring moves, integration announcements, and user complaints. Prefer posts with source links, screenshots, or concrete product details. Skip generic brand mentions.",
    questions: ["Which competitors matter most?", "What business action should a high-priority signal trigger?"],
  },
].map((starter) => ({
  id: starter.id,
  title: starter.title,
  audience: starter.audience,
  default_topic: starter.default_topic,
  starter_brief: starter.brief,
  coach_questions: starter.questions,
  supported_fields: ["search_rules", "rejection_rules", "report_labels"],
})) satisfies ProfileTemplate[];

export function NewProfilePanel({
  busy,
  createProfileFromBrief,
  loadProfileTemplates,
  previewProfileFromBrief,
  templates,
  preview,
  latestResult,
}: {
  busy: boolean;
  createProfileFromBrief: (payload: {
    brief: string;
    source_filename?: string;
    source_text?: string;
    source_base64?: string;
    template_id?: string;
    answers?: Record<string, string>;
    preview?: ProfileCreatePreview;
  }) => Promise<ProfileCreateResult>;
  loadProfileTemplates: () => Promise<ProfileTemplateCatalog>;
  previewProfileFromBrief?: (payload: {
    brief: string;
    template_id?: string;
    answers?: Record<string, string>;
    source_filename?: string;
    source_text?: string;
    source_base64?: string;
    confirm_external_ai?: boolean;
  }) => Promise<ProfileCreatePreview>;
  templates: ProfileTemplate[];
  preview?: ProfileCreatePreview | null;
  latestResult: ProfileCreateResult | null;
}) {
  const [open, setOpen] = useState(false);
  const availableTemplates = templates.length ? templates : PROFILE_STARTERS;
  const [selectedTemplateId, setSelectedTemplateId] = useState(availableTemplates[0]?.id ?? "jobs");
  const [brief, setBrief] = useState("");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [filePayload, setFilePayload] = useState<{ name: string; text?: string; base64?: string } | null>(null);
  const [localError, setLocalError] = useState("");
  const [localPreview, setLocalPreview] = useState<ProfileCreatePreview | null>(null);
  const currentPreview = preview ?? localPreview;
  const selectedTemplate = useMemo(
    () => availableTemplates.find((template) => template.id === selectedTemplateId) ?? availableTemplates[0],
    [availableTemplates, selectedTemplateId],
  );
  const hasInput = Boolean(brief.trim() || filePayload);

  useEffect(() => {
    if (!open || templates.length) {
      return;
    }
    void loadProfileTemplates().catch((error) => setLocalError(error instanceof Error ? error.message : "Could not load profile templates."));
  }, [loadProfileTemplates, open, templates.length]);

  useEffect(() => {
    if (!availableTemplates.some((template) => template.id === selectedTemplateId) && availableTemplates[0]) {
      setSelectedTemplateId(availableTemplates[0].id);
    }
  }, [availableTemplates, selectedTemplateId]);

  async function handleFile(file: File | null) {
    setLocalError("");
    setFilePayload(null);
    if (!file) {
      return;
    }
    const suffix = file.name.split(".").pop()?.toLowerCase() ?? "";
    if (!["md", "markdown", "txt", "pdf"].includes(suffix)) {
      setLocalError("Use a profile file: .md, .txt, or .pdf.");
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

  async function previewProfile() {
    if (!hasInput || busy) {
      return;
    }
    setLocalError("");
    try {
      if (!previewProfileFromBrief) {
        throw new Error("Profile preview is not available right now.");
      }
      const result = await previewProfileFromBrief({
        brief: brief.trim(),
        template_id: selectedTemplateId,
        answers,
        source_filename: filePayload?.name,
        source_text: filePayload?.text,
        source_base64: filePayload?.base64,
        confirm_external_ai: true,
      });
      setLocalPreview(result);
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : "Could not preview this profile.");
    }
  }

  async function submitProfile() {
    if (!hasInput || busy || currentPreview?.status !== "ready") {
      return;
    }
    setLocalError("");
    try {
      await createProfileFromBrief({
        brief: brief.trim(),
        template_id: selectedTemplateId,
        answers,
        source_filename: filePayload?.name,
        source_text: filePayload?.text,
        source_base64: filePayload?.base64,
        preview: currentPreview,
      });
      setBrief("");
      setAnswers({});
      setFilePayload(null);
      setLocalPreview(null);
      setOpen(false);
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : "Could not save this profile.");
    }
  }

  return (
    <section className="new-profile-panel" data-open={open ? "true" : "false"} aria-label="Create a profile">
      <button className="new-profile-toggle" type="button" onClick={() => setOpen((value) => !value)} aria-expanded={open}>
        <Plus size={15} />
        <span>New profile</span>
        <small>Start with a template, add what matters, and review rules before saving.</small>
      </button>
      {open && (
        <div className="new-profile-body">
          <div className="new-profile-starters" aria-label="Profile templates">
            <span>Choose a template</span>
            <div>
              {availableTemplates.map((starter) => (
                <button
                  aria-pressed={starter.id === selectedTemplateId}
                  disabled={busy}
                  key={starter.id}
                  onClick={() => {
                    setSelectedTemplateId(starter.id);
                    setBrief(starter.starter_brief);
                    setLocalPreview(null);
                    setLocalError("");
                  }}
                  type="button"
                >
                  {starter.title}
                </button>
              ))}
            </div>
          </div>
          {selectedTemplate && (
            <div className="new-profile-template-summary">
              <span className="panel-kicker">{selectedTemplate.audience}</span>
              <strong>{selectedTemplate.title}</strong>
              <small>Focus: {selectedTemplate.default_topic}</small>
            </div>
          )}
          <label>
            <span>What should Signal Desk watch for?</span>
            <textarea
              value={brief}
              onChange={(event) => {
                setBrief(event.target.value);
                setLocalPreview(null);
              }}
              disabled={busy}
              placeholder="Example: Watch for senior remote AI engineering roles, paid agent projects, or founder requests that match my background. Avoid unpaid internships and vague promos."
            />
          </label>
          <div className="new-profile-answers" aria-label="Profile questions">
            {(selectedTemplate?.coach_questions ?? []).slice(0, 3).map((question, index) => (
              <label key={question}>
                <span>{question}</span>
                <input
                  value={answers[`q${index + 1}`] ?? ""}
                  onChange={(event) => {
                    setAnswers((current) => ({ ...current, [`q${index + 1}`]: event.target.value }));
                    setLocalPreview(null);
                  }}
                  disabled={busy}
                />
              </label>
            ))}
            <label>
              <span>Must include</span>
              <input
                value={answers.must_have ?? ""}
                onChange={(event) => {
                  setAnswers((current) => ({ ...current, must_have: event.target.value }));
                  setLocalPreview(null);
                }}
                disabled={busy}
              />
            </label>
            <label>
              <span>Never match</span>
              <input
                value={answers.avoid ?? ""}
                onChange={(event) => {
                  setAnswers((current) => ({ ...current, avoid: event.target.value }));
                  setLocalPreview(null);
                }}
                disabled={busy}
              />
            </label>
          </div>
          <label className="new-profile-file">
            <FileUp size={15} />
            <span>{filePayload ? filePayload.name : "Attach .md, .txt, or .pdf"}</span>
            <input
              type="file"
              accept=".md,.markdown,.txt,.pdf,text/markdown,text/plain,application/pdf"
              disabled={busy}
              onChange={(event) => void handleFile(event.target.files?.[0] ?? null)}
            />
          </label>
          {currentPreview && (
            <div className="new-profile-preview" aria-label="Profile preview">
              <span className="panel-kicker">{currentPreview.status === "ready" ? "Ready to review" : "Needs a bit more detail"}</span>
              <strong>{currentPreview.title}</strong>
              {currentPreview.warnings.map((warning) => <small key={warning}>{warning}</small>)}
              {currentPreview.questions.length > 0 && currentPreview.status !== "ready" && (
                <ul>
                  {currentPreview.questions.map((question) => <li key={question}>{question}</li>)}
                </ul>
              )}
              {currentPreview.status === "ready" && (
                <div className="new-profile-preview-rules">
                  <span>Match when</span>
                  <ul>{currentPreview.search_rules.slice(0, 4).map((rule) => <li key={rule}>{rule}</li>)}</ul>
                  <span>Ignore when</span>
                  <ul>{currentPreview.rejection_rules.slice(0, 4).map((rule) => <li key={rule}>{rule}</li>)}</ul>
                </div>
              )}
            </div>
          )}
          <div className="new-profile-actions">
            <button className="text-button profile-primary-action" type="button" disabled={busy || !hasInput} onClick={() => void previewProfile()}>
              <Sparkles size={15} />
              <span>{busy ? "Previewing" : "Preview rules"}</span>
            </button>
            <button className="text-button" type="button" disabled={busy || currentPreview?.status !== "ready"} onClick={() => void submitProfile()}>
              <Check size={15} />
              <span>{busy ? "Saving" : "Save profile"}</span>
            </button>
            <button className="text-button secondary" type="button" disabled={busy} onClick={() => setOpen(false)}>
              <span>Cancel</span>
            </button>
          </div>
          <small className="new-profile-note">
            Saved profiles stay local. You can review these rules before running them.
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
