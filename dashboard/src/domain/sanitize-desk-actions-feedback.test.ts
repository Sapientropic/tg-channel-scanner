import { describe, expect, it } from "vitest";

import {
  sanitizeDeskActions,
  sanitizeDeskActionResult,
  sanitizeFeedbackClearResult,
  sanitizeFeedbackExportResult,
  sanitizeFeedbackProfileSuggestionsResult,
  sanitizeGitUpdateStatus,
  sanitizeProfileCoachPreview,
  sanitizeProfileCreateResult,
  sanitizeProfileCreatePreview,
  sanitizeProfileTemplateCatalog,
} from "./sanitize";
import {
  sanitizeDeskActionResult as sanitizeDashboardModuleDeskActionResult,
  sanitizeFeedbackExportResult as sanitizeDashboardModuleFeedbackExportResult,
} from "./sanitize/dashboard";
import {
  sanitizeDeskActionResult as sanitizeDeskModuleDeskActionResult,
  sanitizeFeedbackExportResult as sanitizeDeskModuleFeedbackExportResult,
} from "./sanitize/desk";

describe("Desk action and feedback sanitizers", () => {
  it("sanitizes action API response envelopes before view state updates", () => {
    expect(
      sanitizeGitUpdateStatus({
        schema_version: "git_update_status_v1",
        status: " behind ",
        message: "  needs pull  ",
        branch: " main ",
        upstream: 42,
        ahead: -1,
        behind: 2.5,
        dirty: true,
        dirty_count: -3,
        dirty_paths: [" dashboard/package-lock.json ", "../private"],
        repairable_dirty: true,
        repairable_dirty_count: 1,
        dirty_repair_applied: true,
        pull_allowed: false,
        fetched: true,
        pull_output: "  Fast-forward  ",
        desk_build_status: "success",
        desk_build_message: "  Desk rebuilt  ",
        desk_reload_recommended: true,
        desk_restart_scheduled: true,
        desk_reload_delay_ms: 2500,
        checked_at: " 2026-05-10T09:00:00+08:00 ",
      }),
    ).toEqual({
      schema_version: "git_update_status_v1",
      status: "behind",
      message: "needs pull",
      branch: "main",
      upstream: undefined,
      repo_url: undefined,
      head: undefined,
      remote_head: undefined,
      ahead: 0,
      behind: 0,
      dirty: true,
      dirty_count: 0,
      dirty_paths: ["dashboard/package-lock.json"],
      repairable_dirty: true,
      repairable_dirty_count: 1,
      dirty_repair_applied: true,
      pull_allowed: false,
      fetched: true,
      pull_output: "Fast-forward",
      desk_build_status: "success",
      desk_build_message: "Desk rebuilt",
      desk_reload_recommended: true,
      desk_restart_scheduled: true,
      desk_reload_delay_ms: 2500,
      checked_at: "2026-05-10T09:00:00+08:00",
    });
    expect(
      sanitizeGitUpdateStatus({
        status: "behind",
        message: "missing schema",
        branch: "main",
        ahead: 0,
        behind: 1,
        dirty: false,
        dirty_count: 0,
        pull_allowed: true,
        checked_at: "2026-05-10T09:00:00+08:00",
      }),
    ).toBeNull();
    expect(sanitizeGitUpdateStatus({ message: "missing status", branch: "main" })).toBeNull();
    expect(sanitizeGitUpdateStatus({ status: " ", branch: "main" })).toBeNull();
    expect(sanitizeGitUpdateStatus({ status: "behind", branch: " " })).toBeNull();
    expect(
      sanitizeGitUpdateStatus({
        schema_version: "git_update_status_v1",
        status: "clean",
        message: 42,
        branch: "main",
        upstream: " ",
        ahead: 0,
        behind: 0,
        dirty: "true",
        dirty_count: 0,
        pull_allowed: "false",
        checked_at: "",
      }),
    ).toMatchObject({
      status: "clean",
      message: "",
      branch: "main",
      upstream: undefined,
      ahead: 0,
      behind: 0,
      dirty: false,
      dirty_count: 0,
      pull_allowed: false,
      checked_at: "",
    });
    expect(
      sanitizeFeedbackExportResult({
        schema_version: "feedback_export_result_v1",
        feedback_count: 2,
        output_path: " output/feedback/review-feedback.jsonl ",
        changed_since_last_export: true,
        exported_at: " 2026-05-10T00:00:00Z ",
      }),
    ).toEqual({
      schema_version: "feedback_export_result_v1",
      feedback_count: 2,
      output_path: "output/feedback/review-feedback.jsonl",
      changed_since_last_export: true,
      exported_at: "2026-05-10T00:00:00Z",
    });
    expect(sanitizeFeedbackExportResult({ schema_version: "feedback_export_result_v1", feedback_count: 0, output_path: "out.jsonl" })).toEqual({
      schema_version: "feedback_export_result_v1",
      feedback_count: 0,
      output_path: "out.jsonl",
    });
    expect(sanitizeFeedbackExportResult({ feedback_count: 1, output_path: "output/feedback/review-feedback.jsonl" })).toBeNull();
    expect(sanitizeFeedbackExportResult({ schema_version: "feedback_export_result_v1", feedback_count: 1, output_path: 42 })).toBeNull();
    expect(
      sanitizeFeedbackExportResult({
        schema_version: "feedback_export_result_v1",
        feedback_count: Number.NaN,
        output_path: "output/feedback/review-feedback.jsonl",
      }),
    ).toBeNull();
    expect(
      sanitizeFeedbackExportResult({
        schema_version: "feedback_export_result_v1",
        feedback_count: -1,
        output_path: "output/feedback/review-feedback.jsonl",
      }),
    ).toBeNull();
    expect(
      sanitizeFeedbackExportResult({
        schema_version: "feedback_export_result_v1",
        feedback_count: 1.5,
        output_path: "output/feedback/review-feedback.jsonl",
      }),
    ).toBeNull();
    expect(sanitizeFeedbackExportResult({ schema_version: "feedback_export_result_v1", feedback_count: 1, output_path: "   " })).toBeNull();
    for (const output_path of [
      "C:/Users/Administrator/private/review-feedback.jsonl",
      "C:\\Users\\Administrator\\private\\review-feedback.jsonl",
      "../private/review-feedback.jsonl",
      "output/feedback/../private.jsonl",
      "file:///tmp/review-feedback.jsonl",
      "output/feedback/review\nfeedback.jsonl",
    ]) {
      expect(sanitizeFeedbackExportResult({ schema_version: "feedback_export_result_v1", feedback_count: 1, output_path })).toBeNull();
      expect(sanitizeDeskModuleFeedbackExportResult({ schema_version: "feedback_export_result_v1", feedback_count: 1, output_path })).toBeNull();
      expect(sanitizeDashboardModuleFeedbackExportResult({ schema_version: "feedback_export_result_v1", feedback_count: 1, output_path })).toBeNull();
    }
    expect(
      sanitizeDashboardModuleFeedbackExportResult({
        schema_version: "feedback_export_result_v1",
        feedback_count: 2,
        output_path: " output\\feedback\\review-feedback.jsonl ",
      }),
    ).toEqual({
      schema_version: "feedback_export_result_v1",
      feedback_count: 2,
      output_path: "output/feedback/review-feedback.jsonl",
    });
    expect(
      sanitizeFeedbackProfileSuggestionsResult({
        schema_version: "feedback_profile_suggestions_result_v1",
        created_count: 1,
        existing_count: 2,
        skipped_count: 0,
        patch_ids: [" patch-1 ", 42, "patch-2"],
        profile_ids: [" jobs-fast "],
        detail: " Profile drafts ready ",
        generated_at: " 2026-05-10T00:00:00Z ",
      }),
    ).toEqual({
      schema_version: "feedback_profile_suggestions_result_v1",
      created_count: 1,
      existing_count: 2,
      skipped_count: 0,
      patch_ids: ["patch-1", "patch-2"],
      profile_ids: ["jobs-fast"],
      detail: "Profile drafts ready",
      generated_at: "2026-05-10T00:00:00Z",
    });
    expect(sanitizeFeedbackProfileSuggestionsResult({ created_count: 1, existing_count: 0, skipped_count: 0 })).toBeNull();
    expect(
      sanitizeFeedbackProfileSuggestionsResult({
        schema_version: "feedback_profile_suggestions_result_v1",
        created_count: -1,
        existing_count: 0,
        skipped_count: 0,
      }),
    ).toBeNull();
    expect(sanitizeFeedbackClearResult({ schema_version: "feedback_clear_result_v1", cleared_count: 2 })).toEqual({
      schema_version: "feedback_clear_result_v1",
      cleared_count: 2,
    });
    expect(sanitizeFeedbackClearResult({ cleared_count: 2 })).toBeNull();
    expect(sanitizeFeedbackClearResult({ schema_version: "feedback_clear_result_v1", cleared_count: 1.5 })).toBeNull();
    expect(
      sanitizeProfileCreateResult({
        schema_version: "desk_profile_create_result_v1",
        profile_id: " jobs-fast ",
        display_name: " Jobs Fast ",
        profile_path: " profiles/jobs-fast.md ",
        created: true,
        detail: " Created profile ",
        next_action: " Review it ",
      }),
    ).toEqual({
      schema_version: "desk_profile_create_result_v1",
      profile_id: "jobs-fast",
      display_name: "Jobs Fast",
      profile_path: "profiles/jobs-fast.md",
      created: true,
      detail: "Created profile",
      next_action: "Review it",
      created_at: undefined,
    });
    expect(
      sanitizeProfileCreateResult({
        profile_id: "jobs-fast",
        display_name: "Jobs Fast",
        profile_path: "profiles/jobs-fast.md",
      }),
    ).toBeNull();
    expect(
      sanitizeProfileTemplateCatalog({
        schema_version: "desk_profile_template_catalog_v1",
        templates: [
          {
            id: " jobs ",
            title: " Developer opportunities ",
            audience: " Builders ",
            default_topic: " jobs ",
            starter_brief: " Track paid frontend work. ",
            coach_questions: [" Must have? ", "Avoid?"],
            supported_fields: ["search_rules", "rejection_rules"],
            raw_path: "C:/Users/Administrator/private/jobs.md",
          },
        ],
      }),
    ).toEqual({
      schema_version: "desk_profile_template_catalog_v1",
      templates: [
        {
          id: "jobs",
          title: "Developer opportunities",
          audience: "Builders",
          default_topic: "jobs",
          starter_brief: "Track paid frontend work.",
          coach_questions: ["Must have?", "Avoid?"],
          supported_fields: ["search_rules", "rejection_rules"],
        },
      ],
    });
    expect(sanitizeProfileTemplateCatalog({ templates: [] })).toBeNull();
    expect(
      sanitizeProfileCreatePreview({
        schema_version: "desk_profile_create_preview_v1",
        status: " ready ",
        template_id: " jobs ",
        title: " Developer opportunities ",
        topic: " jobs ",
        questions: [" Must have? "],
        search_rules: [" Include paid TypeScript work. "],
        rejection_rules: [" Reject unpaid internships. "],
        keywords: [" TypeScript ", "react"],
        markdown_preview: "# Profile",
        warnings: [" Local scaffold used. "],
        generated_rules: [" Include paid TypeScript work. "],
        llm_used: true,
        source_text: "raw private text",
      }),
    ).toEqual({
      schema_version: "desk_profile_create_preview_v1",
      status: "ready",
      template_id: "jobs",
      title: "Developer opportunities",
      topic: "jobs",
      questions: ["Must have?"],
      generated_rules: ["Include paid TypeScript work."],
      search_rules: ["Include paid TypeScript work."],
      rejection_rules: ["Reject unpaid internships."],
      keywords: ["TypeScript", "react"],
      markdown_preview: "# Profile",
      warnings: ["Local scaffold used."],
      llm_used: true,
    });
    expect(sanitizeProfileCreatePreview({ schema_version: "desk_profile_create_preview_v1", status: "broken" })).toBeNull();
    expect(
      sanitizeProfileCoachPreview({
        schema_version: "profile_coach_preview_v1",
        status: " ready ",
        profile_id: " jobs-fast ",
        confidence: " medium ",
        evidence_counts: { keep: 1, skip: 2, false_positive: 3, follow_up: 4, raw: "ignored" },
        diagnosis: [{ label: " False positives ", detail: " Need tighter exclusions. ", raw_note: "ignored" }],
        suspected_false_positive_patterns: [" full-stack generalists "],
        suggested_preference_rules: [" Exclude full-stack roles. "],
        source_suggestions: [{ kind: "review_sources", label: "Review noisy sources", detail: "Check recurring wrong matches." }],
        warnings: [" AI fallback used. "],
        llm_used: true,
      }),
    ).toEqual({
      schema_version: "profile_coach_preview_v1",
      status: "ready",
      profile_id: "jobs-fast",
      confidence: "medium",
      evidence_counts: { keep: 1, skip: 2, false_positive: 3, follow_up: 4 },
      diagnosis: [{ label: "False positives", detail: "Need tighter exclusions." }],
      suspected_false_positive_patterns: ["full-stack generalists"],
      suggested_preference_rules: ["Exclude full-stack roles."],
      source_suggestions: [{ kind: "review_sources", label: "Review noisy sources", detail: "Check recurring wrong matches." }],
      warnings: ["AI fallback used."],
      llm_used: true,
    });
    expect(sanitizeProfileCoachPreview({ schema_version: "profile_coach_preview_v1", status: "ready" })).toBeNull();
  });

  it("sanitizes Desk action payloads without trusting backend-only fields", () => {
    const actions = sanitizeDeskActions({
      schema_version: "desk_actions_v1",
      actions: [
        {
          schema_version: "desk_action_v1",
          action_id: " monitor_jobs_dry_run ",
          group: " run ",
          title: " Dry-run monitor ",
          detail: "Preview local report generation.",
          run_mode: "execute",
          display_command: " tgcs monitor run --profile-id jobs-fast --delivery-mode dry-run ",
          next_action: "Open the report.",
          argv: ["monitor", "run"],
        },
        {
          schema_version: "desk_action_v1",
          action_id: "schedule_install_dry_run",
          group: "Schedule",
          title: "Turn on auto scan",
          detail: "Create a local practice scan schedule.",
          run_mode: "confirm_execute",
          display_command: "Windows Task Scheduler: jobs-fast dry-run",
          next_action: "Review future cards in Signal Desk.",
          argv: ["blocked", "frontend", "must", "ignore"],
        },
        { action_id: "broken", title: "Missing required fields" },
        "bad",
      ],
    });

    expect(actions).toEqual([
      {
        schema_version: "desk_action_v1",
        action_id: "monitor_jobs_dry_run",
        group: "run",
        title: "Dry-run monitor",
        detail: "Preview local report generation.",
        run_mode: "execute",
        display_command: "tgcs monitor run --profile-id jobs-fast --delivery-mode dry-run",
        next_action: "Open the report.",
      },
      {
        schema_version: "desk_action_v1",
        action_id: "schedule_install_dry_run",
        group: "Schedule",
        title: "Turn on auto scan",
        detail: "Create a local practice scan schedule.",
        run_mode: "confirm_execute",
        display_command: "Windows Task Scheduler: jobs-fast dry-run",
        next_action: "Review future cards in Signal Desk.",
      },
    ]);
    expect(actions[0]).not.toHaveProperty("argv");
    expect(actions[1]).not.toHaveProperty("argv");
  });

  it("sanitizes Desk action results for rendering", () => {
    expect(
      sanitizeDeskActionResult({
        schema_version: "desk_action_result_v1",
        action_id: "monitor_jobs_dry_run",
        status: " success ",
        title: " Practice scan complete ",
        detail: "Report ready.",
        display_command: " tgcs monitor run ",
        exit_code: 0,
        artifact_path: " output\\runs\\run-1\\report.html ",
        next_action: "Open the report.",
        finished_at: " 2026-05-10T16:30:00+08:00 ",
        source_access: {
          schema_version: "desk_source_access_health_v1",
          source_count: 8,
          checked_count: 6,
          accessible_count: 3,
          quiet_count: 1,
          inaccessible_count: 2,
          truncated_count: 2,
          probe_window_hours: 24,
          probe_window_hours_min: 24,
          probe_window_hours_max: 24,
          reason_counts: { cannot_resolve_entity: 2, bad: "ignored" },
        },
        stdout: "ignored",
      }),
    ).toEqual({
      schema_version: "desk_action_result_v1",
      action_id: "monitor_jobs_dry_run",
      status: "success",
      title: "Practice scan complete",
      detail: "Report ready.",
      display_command: "tgcs monitor run",
      exit_code: 0,
      artifact_path: "output/runs/run-1/report.html",
      next_action: "Open the report.",
      finished_at: "2026-05-10T16:30:00+08:00",
      source_access: {
        schema_version: "desk_source_access_health_v1",
        checked_at: "",
        source_count: 8,
        checked_count: 6,
        accessible_count: 3,
        quiet_count: 1,
        inaccessible_count: 2,
        truncated_count: 2,
        probe_window_hours: 24,
        probe_window_hours_min: 24,
        probe_window_hours_max: 24,
        reason_counts: { cannot_resolve_entity: 2 },
      },
    });

    expect(
      sanitizeDeskActionResult({
        schema_version: "desk_action_result_v1",
        action_id: "login_human",
        status: "needs_human",
        title: "Login requires terminal",
        display_command: "tgcs login",
        exit_code: "not-a-number",
      }),
    ).toMatchObject({
      schema_version: "desk_action_result_v1",
      action_id: "login_human",
      status: "needs_human",
      exit_code: null,
    });
    expect(sanitizeDeskActionResult({ status: "success", title: "Missing id" })).toBeNull();
    expect(
      sanitizeDeskActionResult({
        action_id: "monitor_jobs_dry_run",
        status: "success",
        title: "Missing schema",
        display_command: "tgcs monitor run --profile-id jobs-fast --delivery-mode dry-run",
      }),
    ).toBeNull();
    expect(sanitizeDeskActionResult({ action_id: "feedback_export", status: " ", title: "Bad status" })).toBeNull();
    for (const artifact_path of [
      "output/feedback/review-feedback.jsonl",
      "C:/Users/Administrator/private/report.html",
      "output/runs/run-1/../secret-report.html",
      "https://example.com/report.html",
    ]) {
      const payload = {
        schema_version: "desk_action_result_v1" as const,
        action_id: "monitor_jobs_dry_run",
        status: "success",
        title: "Report ready",
        display_command: "tgcs monitor run",
        artifact_path,
      };
      expect(sanitizeDeskActionResult(payload)?.artifact_path).toBe("");
      expect(sanitizeDeskModuleDeskActionResult(payload)?.artifact_path).toBe("");
      expect(sanitizeDashboardModuleDeskActionResult(payload)?.artifact_path).toBe("");
    }
  });
});
