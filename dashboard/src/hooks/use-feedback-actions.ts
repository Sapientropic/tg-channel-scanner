import { useState, type Dispatch, type SetStateAction } from "react";

import {
  clearFeedbackDecisions as clearFeedbackDecisionsRequest,
  errorMessage,
  exportFeedback as exportFeedbackRequest,
  generateFeedbackProfileSuggestions as generateFeedbackProfileSuggestionsRequest,
  undoReviewCardAction,
} from "../api/client";
import type { FeedbackExportResult, FeedbackProfileSuggestionsResult, Tab } from "../domain/types";

type Notice = { tone: "success" | "error"; text: string };

type UseFeedbackActionsOptions = {
  refresh: () => Promise<void>;
  setActiveTab: Dispatch<SetStateAction<Tab>>;
  setBusy: Dispatch<SetStateAction<boolean>>;
  setNotice: Dispatch<SetStateAction<Notice | null>>;
};

export function useFeedbackActions({
  refresh,
  setActiveTab,
  setBusy,
  setNotice,
}: UseFeedbackActionsOptions) {
  const [feedbackExport, setFeedbackExport] = useState<FeedbackExportResult | null>(null);
  const [feedbackProfileSuggestions, setFeedbackProfileSuggestions] = useState<FeedbackProfileSuggestionsResult | null>(null);

  async function exportFeedback() {
    setBusy(true);
    setNotice(null);
    try {
      const result = await exportFeedbackRequest();
      setFeedbackExport(result);
      await refresh();
      setNotice({ tone: "success", text: `${result.feedback_count} decisions applied to future reports` });
    } catch (error) {
      setNotice({ tone: "error", text: feedbackClearErrorMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  async function generateFeedbackProfileSuggestions() {
    setBusy(true);
    setNotice(null);
    try {
      const result = await generateFeedbackProfileSuggestionsRequest();
      setFeedbackProfileSuggestions(result);
      await refresh();
      if (result.created_count > 0 || result.existing_count > 0) {
        setActiveTab("profiles");
      }
      setNotice({ tone: "success", text: result.detail || "Profile suggestions updated" });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  async function clearFeedback() {
    setBusy(true);
    setNotice(null);
    let successText = "";
    try {
      const clearedCount = await clearFeedbackDecisionsRequest();
      setFeedbackExport(null);
      await refresh();
      successText = clearedCount > 0 ? `${clearedCount} learning decisions cleared` : "No learning decisions to clear";
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setBusy(false);
    }
    if (successText) {
      setNotice({ tone: "success", text: successText });
    }
  }

  async function undoFeedbackDecision(cardId: string) {
    if (!cardId) {
      return;
    }
    setBusy(true);
    setNotice(null);
    try {
      await undoReviewCardAction(cardId);
      await refresh();
      setNotice({ tone: "success", text: "Decision undone" });
    } catch (error) {
      setNotice({ tone: "error", text: errorMessage(error) });
    } finally {
      setBusy(false);
    }
  }

  return {
    feedbackExport,
    feedbackProfileSuggestions,
    exportFeedback,
    generateFeedbackProfileSuggestions,
    clearFeedback,
    undoFeedbackDecision,
  };
}

function feedbackClearErrorMessage(error: unknown) {
  const message = errorMessage(error);
  if (/404|not found/i.test(message)) {
    return "Signal Desk server is out of date. Close and reopen Signal Desk, then retry the learning action.";
  }
  return message;
}
