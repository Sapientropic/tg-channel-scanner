import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  MiniAppCard,
  MiniAppLearningLoop,
  MiniAppSoundToggle,
  MiniAppSourceDiscovery,
  miniappActionStatus,
  miniappCueForAction,
  miniappFilterCards,
  miniappFilterAriaLabel,
  miniappFilterOptions,
  miniappContextItems,
  miniappQueueSummary,
  miniappReviewCards,
  miniappSourceLinks,
  miniappStateDetail,
  miniappStatusLine,
  miniappTriggerHaptic,
  telegramSupportsWebAppVersion,
} from "./miniapp";
import type { ReviewCard } from "./domain/types";

const card: ReviewCard = {
  schema_version: "review_card_v1",
  card_id: "card-1",
  profile_id: "jobs-fast",
  title: "Frontend Mini App contract",
  rating: "high",
  decision_status: "new",
  source_refs: [{ channel: "miniapps_jobs", id: 42, url: "https://t.me/miniapps_jobs/42" }],
  item: { why: "Paid React work with clear budget." },
  status: "pending",
  opportunity_status: "open",
  opportunity_updated_at: "2026-05-17T00:00:00Z",
  report_path: "output/jobs-fast/report.html",
  updated_at: "2026-05-17T00:00:00Z",
};

const sourceRecommendations = [
  {
    schema_version: "miniapp_source_recommendation_v1" as const,
    source_id: "telegram:remote_frontend_jobs",
    channel: "remote_frontend_jobs",
    label: "Remote Front-End Jobs",
    topic: "jobs",
    reason: "Remote front-end jobs with medium expected noise.",
    installed: false,
  },
  {
    schema_version: "miniapp_source_recommendation_v1" as const,
    source_id: "telegram:remote_ai_jobs",
    channel: "remote_ai_jobs",
    label: "Remote AI/ML/Data Science Jobs",
    topic: "jobs",
    reason: "Remote AI, ML, and data science jobs.",
    installed: true,
  },
];

describe("Telegram Mini App review shell", () => {
  it("prioritizes open pending cards before handled cards", () => {
    expect(
      miniappReviewCards([
        { ...card, card_id: "handled", status: "kept" },
        { ...card, card_id: "open-low", rating: "low" },
        { ...card, card_id: "open-high", rating: "high" },
      ]).map((item) => item.card_id),
    ).toEqual(["open-high", "open-low", "handled"]);
  });

  it("derives a compact mobile queue with review filters", () => {
    const cards: ReviewCard[] = [
      card,
      { ...card, card_id: "medium", rating: "medium", decision_status: "seen" },
      { ...card, card_id: "saved", opportunity_status: "saved" },
      { ...card, card_id: "handled", status: "kept" },
    ];

    expect(miniappQueueSummary(cards)).toEqual({
      total: 4,
      review: 2,
      priority: 1,
      saved: 1,
      handled: 1,
      duplicate: 0,
    });
    expect(miniappFilterCards(cards, "review").map((item) => item.card_id)).toEqual(["card-1", "medium"]);
    expect(miniappFilterCards(cards, "priority").map((item) => item.card_id)).toEqual(["card-1"]);
    expect(miniappFilterOptions(cards).map((option) => option.id)).toEqual(["review", "priority", "saved", "handled", "all"]);
  });

  it("labels review filters with their current result count for accessibility", () => {
    expect(miniappFilterAriaLabel({ label: "Review", count: 2 })).toBe("Show Review cards, 2 results");
    expect(miniappFilterAriaLabel({ label: "Priority", count: 1 })).toBe("Show Priority cards, 1 result");
  });

  it("renders mobile lifecycle actions and safe detail links without local Desk chrome", () => {
    const html = renderToStaticMarkup(
      <MiniAppCard
        card={card}
        busy={false}
        onAct={() => undefined}
      />,
    );

    expect(html).toContain("Frontend Mini App contract");
    expect(html).toContain("Applied");
    expect(html).toContain("Save");
    expect(html).toContain("Not a fit");
    expect(html).toContain("Feedback");
    expect(html).toContain('aria-label="Mark Frontend Mini App contract as applied"');
    expect(html).toContain('aria-label="Save Frontend Mini App contract for later"');
    expect(html).toContain('aria-label="Mark Frontend Mini App contract as not a fit"');
    expect(html).toContain('aria-label="Open feedback for Frontend Mini App contract"');
    expect(html).toContain('data-expanded="false"');
    expect(html).toContain('aria-expanded="false"');
    expect(html).toContain('data-sound-cue="positive"');
    expect(html).toContain('data-sound-cue="negative"');
    expect(html).toContain('data-sound-cue="tick"');
    expect(html).toContain("Scan details");
    expect(html).toContain('aria-label="Open scan details for Frontend Mini App contract"');
    expect(html).toContain("/artifacts/output%2Fjobs-fast%2Freport.html");
    expect(html).toContain("Open in Telegram");
    expect(html).toContain('aria-label="Open Miniapps Jobs in Telegram"');
    expect(html).toContain('aria-label="Card status and time"');
    expect(html).toContain("Open</span>");
    expect(html).not.toContain('<div class="miniapp-meta" aria-label="Card status and time"><span>New</span>');
    expect(html).not.toContain(">https://t.me/miniapps_jobs/42<");
    expect(html).not.toContain("Signal Desk");
    expect(html).not.toContain("Settings");
  });

  it("renders feedback tuning controls with clear close and duplicate states", () => {
    const html = renderToStaticMarkup(
      <MiniAppCard
        card={card}
        busy={false}
        initialTuningOpen={true}
        onAct={() => undefined}
      />,
    );

    expect(html).toContain('aria-expanded="true"');
    expect(html).toContain("Prefer similar");
    expect(html).toContain('data-review-action="duplicate"');
    expect(html).toContain('data-tone="negative"');
    expect(html).toContain('aria-label="Close feedback"');
    expect(html).toContain("miniapp-note-close");
  });

  it("renders original source excerpt safely on mobile cards", () => {
    const html = renderToStaticMarkup(
      <MiniAppCard
        card={{ ...card, item: { ...card.item, source_excerpt: "Original post: React Mini App contract with clear weekly budget. [link]" } }}
        busy={false}
        onAct={() => undefined}
      />,
    );

    expect(html).toContain("Source excerpt");
    expect(html).toContain("Jump clue:");
    expect(html).toContain("React Mini App contract with clear weekly budget.");
    expect(html).not.toContain("[link]");
    expect(html).not.toContain("Original post:");
    expect(html).toContain("Worth opening to verify original details before acting.");
  });

  it("explains why opening the original source is worth it when fields changed", () => {
    const html = renderToStaticMarkup(
      <MiniAppCard
        card={{
          ...card,
          item: {
            ...card.item,
            source_excerpt: "Looking for senior React contractor with visible budget.",
            decision_state: { status: "changed", material_change_fields: ["budget", "remote"] },
          },
        }}
        busy={false}
        onAct={() => undefined}
      />,
    );

    expect(html).toContain("Worth opening to verify Budget and Remote before acting.");
  });

  it("renders recovery actions for handled cards", () => {
    const html = renderToStaticMarkup(
      <MiniAppCard
        card={{ ...card, status: "kept", opportunity_status: "saved" }}
        busy={false}
        onAct={() => undefined}
      />,
    );

    expect(html).toContain("Undo");
    expect(html).toContain("Reopen");
  });

  it("surfaces duplicate cards as a first-class mobile filter", () => {
    const cards: ReviewCard[] = [card, { ...card, card_id: "duplicate", opportunity_status: "duplicate" }];

    expect(miniappQueueSummary(cards).duplicate).toBe(1);
    expect(miniappFilterCards(cards, "duplicate").map((item) => item.card_id)).toEqual(["duplicate"]);
    expect(miniappFilterOptions(cards).map((option) => option.id)).toContain("duplicate");
  });

  it("hides local scan artifact links outside loopback preview mode", () => {
    const html = renderToStaticMarkup(
      <MiniAppCard
        allowReportLinks={false}
        card={card}
        busy={false}
        onAct={() => undefined}
      />,
    );

    expect(html).not.toContain("Scan details");
    expect(html).not.toContain("/artifacts/");
  });

  it("shows changed-field evidence consistently with desktop review cards", () => {
    const changedCard: ReviewCard = {
      ...card,
      decision_status: "changed",
      item: {
        why: "Budget and location changed.",
        decision_state: {
          status: "changed",
          material_change_fields: ["salary_range", "location", "contract_type"],
        },
      },
    };

    expect(miniappContextItems(changedCard)).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          key: "changed-fields",
          label: "Changed",
          value: "Salary Range +1",
        }),
      ]),
    );
  });

  it("renders multiple Telegram source links without exposing local reports in Telegram mode", () => {
    const multiSourceCard: ReviewCard = {
      ...card,
      source_refs: [
        { channel: "miniapps_jobs", id: 42, url: "https://t.me/miniapps_jobs/42" },
        { channel: "design_leads", id: 77, url: "https://t.me/design_leads/77" },
        { channel: "design_leads", id: 77, url: "https://t.me/design_leads/77" },
        { channel: "frontend_feed", id: 90, url: "https://t.me/frontend_feed/90" },
        { channel: "hidden_feed", id: 91, url: "https://t.me/hidden_feed/91" },
      ],
    };

    expect(miniappSourceLinks(multiSourceCard).map((item) => item.label)).toEqual([
      "Miniapps Jobs",
      "Design Leads",
      "Frontend Feed",
    ]);

    const html = renderToStaticMarkup(
      <MiniAppCard
        allowReportLinks={false}
        card={multiSourceCard}
        busy={false}
        onAct={() => undefined}
      />,
    );

    expect(html).toContain("Miniapps Jobs");
    expect(html).toContain("Design Leads");
    expect(html).toContain("Frontend Feed");
    expect(html).toContain("Open in Telegram");
    expect(html).toContain("+1 source");
    expect(html).not.toContain("/artifacts/");
  });

  it("renders source recommendations as a one-tap next-run helper", () => {
    const html = renderToStaticMarkup(
      <MiniAppSourceDiscovery
        busy={false}
        recommendations={sourceRecommendations}
        onAdd={() => undefined}
      />,
    );

    expect(html).toContain("Source discovery");
    expect(html).toContain("Remote Front-End Jobs");
    expect(html).toContain("Remote AI/ML/Data Science Jobs");
    expect(html).toContain("Add recommended channels");
    expect(html).toContain("Starter sources");
    expect(html).toContain("1 to add");
    expect(html).toContain("Next run");
    expect(html).toContain("Metadata only");
    expect(html).toContain("Cards appear after rerun.");
    expect(html).toContain("Channels");
    expect(html).toContain("Swipe 2");
    expect(html).toContain('aria-label="Add 1 recommended source for the next run"');
    expect(html).toContain('aria-label="Recommended source Remote Front-End Jobs"');
    expect(html).toContain("Added");
    expect(html).toContain("Noise med");
    expect(html).not.toContain(">Remote front-end jobs with medium expected noise.<");
    expect(html).not.toContain("https://t.me");
  });

  it("renders installed source recommendations as a ready next-run state", () => {
    const html = renderToStaticMarkup(
      <MiniAppSourceDiscovery
        busy={false}
        recommendations={sourceRecommendations.map((source) => ({ ...source, installed: true }))}
        onAdd={() => undefined}
      />,
    );

    expect(html).toContain('data-ready="true"');
    expect(html).toContain("Starter sources");
    expect(html).toContain("Refresh channels");
    expect(html).toContain("2 ready");
    expect(html).toContain("Next run");
    expect(html).toContain("Metadata only");
    expect(html).toContain("Ready for rerun.");
    expect(html).toContain("Channels");
    expect(html).toContain("Swipe 2");
    expect(html).toContain('aria-label="Refresh 2 ready sources for the next run"');
    expect(html).toContain('aria-label="Added source Remote Front-End Jobs"');
    expect(html).not.toContain("Recommended channels are ready");
    expect(html).not.toContain(">These sources are already installed");
  });

  it("renders a compact learning loop receipt for the next run", () => {
    const html = renderToStaticMarkup(
      <MiniAppLearningLoop
        learning={{
          schema_version: "miniapp_learning_summary_v1",
          current_decision_count: 3,
          exportable_count: 2,
          non_exportable_follow_up_count: 1,
          pending_profile_diff_count: 1,
          applied_profile_diff_count: 0,
          changed_since_last_export: true,
          next_action: {
            label: "Review profile drafts",
            detail: "Profile draft is ready in Desk.",
          },
        }}
      />,
    );

    expect(html).toContain("Learning loop");
    expect(html).toContain("Profile draft");
    expect(html).toContain("3 choices");
    expect(html).toContain("Draft ready");
    expect(html).toContain("New evidence");
    expect(html).toContain("Review drafts");
    expect(html).toContain("Apply in Desk, then rerun.");
    expect(html.match(/Apply in Desk, then rerun\./g)).toHaveLength(1);
    expect(html).toContain('aria-label="Learning loop status"');
    expect(html).toContain('data-active="true"');
    expect(html).not.toContain("Review the profile draft in Desk, then run again to test whether the matches improved.");
    expect(html).not.toContain("Profile draft is ready in Desk.");
  });

  it("maps actions to tiny sound and Telegram haptic cues", () => {
    expect(miniappCueForAction("keep")).toEqual({ tone: "positive", haptic: "success" });
    expect(miniappCueForAction("applied")).toEqual({ tone: "positive", haptic: "success" });
    expect(miniappCueForAction("false_positive")).toEqual({ tone: "negative", haptic: "warning" });
    expect(miniappCueForAction("dismissed")).toEqual({ tone: "negative", haptic: "warning" });
    expect(miniappCueForAction("refresh")).toEqual({ tone: "tick", haptic: "selection" });
  });

  it("triggers Telegram haptic feedback when the Mini App bridge is available", () => {
    const calls: string[] = [];
    miniappTriggerHaptic(
      {
        HapticFeedback: {
          notificationOccurred: (type: string) => calls.push(`notification:${type}`),
          selectionChanged: () => calls.push("selection"),
        },
      },
      { tone: "positive", haptic: "success" },
    );
    miniappTriggerHaptic(
      {
        HapticFeedback: {
          notificationOccurred: (type: string) => calls.push(`notification:${type}`),
          selectionChanged: () => calls.push("selection"),
        },
      },
      { tone: "tick", haptic: "selection" },
    );

    expect(calls).toEqual(["notification:success", "selection"]);
  });

  it("does not call haptic feedback on unsupported Telegram WebApp versions", () => {
    const calls: string[] = [];
    miniappTriggerHaptic(
      {
        version: "6.0",
        HapticFeedback: {
          notificationOccurred: (type: string) => calls.push(`notification:${type}`),
          selectionChanged: () => calls.push("selection"),
        },
      },
      { tone: "positive", haptic: "success" },
    );

    expect(calls).toEqual([]);
  });

  it("renders an accessible sound cue toggle", () => {
    const enabledHtml = renderToStaticMarkup(<MiniAppSoundToggle enabled={true} onToggle={() => undefined} />);
    const mutedHtml = renderToStaticMarkup(<MiniAppSoundToggle enabled={false} onToggle={() => undefined} />);

    expect(enabledHtml).toContain("Mute sound cues");
    expect(enabledHtml).toContain('aria-pressed="true"');
    expect(mutedHtml).toContain("Enable sound cues");
    expect(mutedHtml).toContain('aria-pressed="false"');
  });

  it("formats the Mini App state timestamp as product copy", () => {
    expect(miniappStateDetail("", null, "2026-05-17T17:05:46")).toBe("Updated 05-17 17:05");
    expect(miniappStateDetail("Connection failed", null, "2026-05-17T17:05:46")).toBe("Connection failed");
    expect(miniappStateDetail("", { title: "Feedback saved", detail: "Profile tuning updated." }, "2026-05-17T17:05:46")).toBe("Profile tuning updated.");
    expect(miniappStateDetail("", null, "")).toBe("Reading local state");
  });

  it("summarizes Telegram auth and local preview mode distinctly", () => {
    expect(miniappStatusLine({ source: "telegram", user_id: "123456" })).toBe("Telegram user 123456");
    expect(miniappStatusLine({ source: "loopback_preview" })).toBe("Local preview");
  });

  it("guards newer Telegram theme APIs by WebApp version", () => {
    expect(telegramSupportsWebAppVersion({ version: "6.0" }, "6.1")).toBe(false);
    expect(telegramSupportsWebAppVersion({ version: "6.1" }, "6.1")).toBe(true);
    expect(telegramSupportsWebAppVersion({ version: "7.10" }, "6.1")).toBe(true);
    expect(telegramSupportsWebAppVersion({}, "6.1")).toBe(false);
  });

  it("summarizes saved Mini App actions as review or learning feedback", () => {
    expect(miniappActionStatus("applied")).toEqual({ title: "Applied saved", detail: "Moved out of Review. Open All if you need to undo." });
    expect(miniappActionStatus("saved")).toEqual({ title: "Saved for later", detail: "Moved to Saved. Open Saved or All to revisit." });
    expect(miniappActionStatus("dismissed")).toEqual({ title: "Marked not a fit", detail: "Moved out of Review. Open All if you need to undo." });
    expect(miniappActionStatus("duplicate")).toEqual({ title: "Marked duplicate", detail: "Moved out of Review. Open All if you need to undo." });
    expect(miniappActionStatus("reopen")).toEqual({ title: "Reopened", detail: "Card is back in Review." });
    expect(miniappActionStatus("undo_decision")).toEqual({ title: "Decision cleared", detail: "Card is back in Review." });
    expect(miniappActionStatus("false_positive", { current_decision_count: 2, pending_profile_diff_count: 0 })).toEqual({
      title: "Feedback saved",
      detail: "2 learning choices are ready for a profile draft.",
    });
    expect(miniappActionStatus("follow_up", { current_decision_count: 1, pending_profile_diff_count: 1 })).toEqual({
      title: "Note saved",
      detail: "Profile draft is ready in Desk; apply it before the next run.",
    });
  });
});
