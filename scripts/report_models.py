"""Shared report model types used by Markdown, HTML, and extraction modules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class ReportError(Exception):
    def __init__(
        self,
        message: str,
        raw_response: str | None = None,
        *,
        code: str = "llm_provider_error",
        next_step: str = "",
        retryable: bool = True,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.raw_response = raw_response
        self.code = code
        self.next_step = next_step
        self.retryable = retryable
        self.details = details or {}


@dataclass
class ReportResult:
    markdown: str
    stats: dict
    warnings: list[str]
    diagnostics: list[dict] | None = None
    jobs: list[dict] | None = None
    source_summary: dict | None = None
    state_summary: dict | None = None
    state: dict | None = None


@dataclass
class ExtractionResult:
    items: list[dict]
    llm: dict
