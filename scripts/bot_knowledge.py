"""Small allowlisted local knowledge corpus for the Telegram Bot assistant."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from scripts import report
except ModuleNotFoundError:
    _PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    from scripts import report


PROJECT_ROOT = Path(__file__).resolve().parent.parent

KNOWLEDGE_DOC_ALLOWLIST = (
    "README.md",
    "README.zh-CN.md",
    "SKILL.md",
    "docs/agent-cli-contract.md",
    "docs/desktop-platforms.md",
    "docs/getting-api-credentials.md",
    "profiles/README.md",
    "ROADMAP.md",
)


@dataclass(frozen=True)
class KnowledgeSection:
    path: str
    title: str
    text: str


@dataclass(frozen=True)
class KnowledgeAnswer:
    text: str
    sections: tuple[KnowledgeSection, ...]
    used_llm: bool = False


def _is_chinese(text: str) -> bool:
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _tokens(text: str) -> set[str]:
    lowered = text.casefold()
    words = set(re.findall(r"[a-z0-9_@.-]{2,}", lowered))
    words.update(re.findall(r"[\u4e00-\u9fff]{1,3}", lowered))
    return words


def _split_by_headings(path: str, text: str) -> list[KnowledgeSection]:
    sections: list[KnowledgeSection] = []
    current_title = path
    current_lines: list[str] = []
    for line in text.splitlines():
        heading = re.match(r"^(#{1,4})\s+(.+?)\s*$", line)
        if heading:
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    sections.append(KnowledgeSection(path=path, title=current_title, text=body))
            current_title = heading.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)
    body = "\n".join(current_lines).strip()
    if body:
        sections.append(KnowledgeSection(path=path, title=current_title, text=body))
    return sections


class BotKnowledge:
    def __init__(self, *, root: Path = PROJECT_ROOT, allowlist: tuple[str, ...] = KNOWLEDGE_DOC_ALLOWLIST):
        self.root = root
        self.allowlist = allowlist

    def load_sections(self) -> list[KnowledgeSection]:
        sections: list[KnowledgeSection] = []
        for relative in self.allowlist:
            path = self.root / relative
            if not path.exists() or not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            sections.extend(_split_by_headings(relative, text))
        return sections

    def retrieve(self, question: str, *, limit: int = 4) -> list[KnowledgeSection]:
        query_tokens = _tokens(question)
        if not query_tokens:
            return []
        scored: list[tuple[int, int, KnowledgeSection]] = []
        for index, section in enumerate(self.load_sections()):
            haystack = _tokens(section.title + "\n" + section.text)
            overlap = len(query_tokens.intersection(haystack))
            phrase_bonus = 2 if question.casefold() in section.text.casefold() else 0
            score = overlap + phrase_bonus
            if score > 0:
                scored.append((score, -index, section))
        scored.sort(reverse=True)
        return [section for _, _, section in scored[:limit]]

    def answer(self, question: str, *, use_llm: bool = True) -> KnowledgeAnswer:
        sections = tuple(self.retrieve(question))
        if use_llm:
            llm_text = self._llm_answer(question, sections)
            if llm_text:
                return KnowledgeAnswer(text=llm_text, sections=sections, used_llm=True)
        return KnowledgeAnswer(text=self._fallback_answer(question, sections), sections=sections, used_llm=False)

    def _llm_answer(self, question: str, sections: tuple[KnowledgeSection, ...]) -> str:
        if not sections or not report.llm_key_available():
            return ""
        try:
            from openai import OpenAI
        except ImportError:
            return ""
        base_url, model = report.resolve_llm_settings(None, report.DEFAULT_MODEL)
        provider = report.llm_provider(base_url, model)
        api_key = report.api_key_for_provider(provider)
        if not api_key:
            return ""
        language = "Chinese" if _is_chinese(question) else "English"
        context = [
            {"title": section.title, "text": section.text[:1600]}
            for section in sections[:4]
        ]
        system_prompt = (
            f"Answer in {language}. Use only the provided T-Sense documentation sections. "
            "Be short and operational: direct answer first, one next step, and mention [⚠️] when evidence is missing. "
            "Do not reveal local absolute paths, tokens, chat ids, config dumps, argv, or raw Telegram content."
        )
        user_prompt = json.dumps({"question": question[:1000], "sections": context}, ensure_ascii=False)
        create_kwargs: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": report.llm_temperature(provider),
        }
        thinking_extra = report.minimax_thinking_extra(provider) or report.deepseek_thinking_extra(provider, model)
        if thinking_extra:
            create_kwargs["extra_body"] = thinking_extra
        report.add_token_limit(create_kwargs, provider=provider, max_tokens=350)
        try:
            response = OpenAI(api_key=api_key, base_url=base_url).chat.completions.create(**create_kwargs)
        except Exception:
            return ""
        return (response.choices[0].message.content or "").strip()[:1800]

    def _fallback_answer(self, question: str, sections: tuple[KnowledgeSection, ...]) -> str:
        chinese = _is_chinese(question)
        if not sections:
            if chinese:
                return "[⚠️] 我在本地文档里没有找到足够依据。下一步：打开 Signal Desk 的 Settings 或发送 /help 查看可用动作。"
            return "[⚠️] I could not find enough evidence in the local docs. Next: open Signal Desk Settings or send /help."
        first = sections[0]
        sentence = re.split(r"(?<=[.!?。！？])\s+", " ".join(first.text.split()))[0][:500]
        if chinese:
            return f"{sentence}\n\n下一步：打开 Signal Desk，或发送 /status 查看当前本地状态。"
        return f"{sentence}\n\nNext: open Signal Desk, or send /status to check local setup state."
