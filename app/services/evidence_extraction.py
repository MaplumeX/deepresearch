from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.domain.models import Evidence, EvidenceType, ResearchTask, SourceDocument, SourceRole
from app.services.llm import (
    LLMInvocationError,
    LLMOutputInvalidError,
    build_structured_chat_model,
    ensure_synthesis_llm_ready,
)


_MAX_EVIDENCE_PER_SOURCE = 3
_MAX_SNIPPET_LENGTH = 280
_MAX_CLAIM_LENGTH = 220
_MAX_CANDIDATE_SNIPPETS = 12


class EvidenceDraft(BaseModel):
    claim: str = Field(min_length=1)
    snippet: str = Field(min_length=1)
    evidence_type: EvidenceType = "fact"
    source_role: SourceRole = "unknown"


class EvidenceExtractionDraft(BaseModel):
    items: list[EvidenceDraft] = Field(default_factory=list)


def build_task_evidence(
    task: ResearchTask,
    sources: list[SourceDocument],
    settings: Settings | None = None,
) -> tuple[list[Evidence], list[SourceDocument]]:
    effective_settings = settings or get_settings()
    findings: list[Evidence] = []
    kept_sources: list[SourceDocument] = []

    for source in sources:
        extracted = _extract_source_evidence(task, source, effective_settings)
        if not extracted:
            continue
        kept_sources.append(source)
        findings.extend(extracted)

    return findings, kept_sources


def _extract_source_evidence(
    task: ResearchTask,
    source: SourceDocument,
    settings: Settings,
) -> list[Evidence]:
    items = _extract_source_evidence_with_llm(task, source, settings)
    return [
        item.model_copy(update={"evidence_id": f"{task.task_id}-{item.source_id}-{index}"})
        for index, item in enumerate(items, start=1)
    ]


def _extract_source_evidence_with_llm(
    task: ResearchTask,
    source: SourceDocument,
    settings: Settings,
) -> list[Evidence]:
    ensure_synthesis_llm_ready(settings)

    try:
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError as exc:
        raise LLMInvocationError("Evidence extraction dependencies are not installed.") from exc

    candidate_snippets = _pick_candidate_snippets(source.content, limit=_MAX_CANDIDATE_SNIPPETS)
    if not candidate_snippets:
        return []

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You extract source-grounded evidence for a deep research workflow. "
                "Return at most 3 evidence items. "
                "Each snippet must be copied verbatim from the provided candidate snippets. "
                "Do not invent facts. "
                "Choose the best evidence_type and source_role for each item.",
            ),
            (
                "human",
                "Task title:\n{task_title}\n\n"
                "Task question:\n{task_question}\n\n"
                "Source title:\n{source_title}\n\n"
                "Source URL:\n{source_url}\n\n"
                "Candidate snippets:\n{candidate_snippets}",
            ),
        ]
    )
    model = build_structured_chat_model(settings.synthesis_model, settings, EvidenceExtractionDraft, temperature=0)
    if model is None:
        raise LLMInvocationError("Evidence extraction model could not be initialized.")

    chain = prompt | model
    try:
        response: EvidenceExtractionDraft = chain.invoke(
            {
                "task_title": task.title,
                "task_question": task.question,
                "source_title": source.title,
                "source_url": source.url,
                "candidate_snippets": "\n".join(f"- {snippet}" for snippet in candidate_snippets),
            }
        )
    except Exception as exc:
        raise LLMInvocationError("Evidence extraction failed.") from exc

    validated: list[Evidence] = []
    for item in response.items:
        evidence = _validate_evidence_draft(task, source, item)
        if evidence is None:
            continue
        validated.append(evidence)

    if response.items and not validated:
        raise LLMOutputInvalidError(
            f"Evidence extraction returned no valid evidence for source `{source.source_id}`.",
        )
    return validated[:_MAX_EVIDENCE_PER_SOURCE]


def _validate_evidence_draft(
    task: ResearchTask,
    source: SourceDocument,
    draft: EvidenceDraft,
) -> Evidence | None:
    snippet = _normalize_space(draft.snippet)
    if not snippet:
        return None
    if not _snippet_supported(source.content, snippet):
        return None

    claim = _trim_text(_normalize_space(draft.claim), _MAX_CLAIM_LENGTH)
    if not claim:
        return None

    return Evidence(
        evidence_id="",
        task_id=task.task_id,
        claim=claim,
        snippet=_trim_text(snippet, _MAX_SNIPPET_LENGTH),
        source_id=source.source_id,
        url=source.url,
        title=source.title,
        evidence_type=draft.evidence_type,
        source_role=draft.source_role,
    )


def _pick_candidate_snippets(content: str, *, limit: int) -> list[str]:
    sentences = _split_sentences(content)
    if not sentences:
        snippet = _trim_text(_normalize_space(content), _MAX_SNIPPET_LENGTH)
        return [snippet] if snippet else []

    snippets: list[str] = []
    seen: set[str] = set()
    for index in range(0, len(sentences), 2):
        snippet = _trim_text(" ".join(sentences[index:index + 2]), _MAX_SNIPPET_LENGTH)
        if not snippet:
            continue
        dedupe_key = snippet.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        snippets.append(snippet)
        if len(snippets) >= limit:
            break
    return snippets


def _split_sentences(content: str) -> list[str]:
    normalized = _normalize_space(content)
    if not normalized:
        return []
    parts = re.split(r"(?<=[。！？.!?])\s+|\n+", normalized)
    return [part.strip() for part in parts if part.strip()]


def _snippet_supported(content: str, snippet: str) -> bool:
    normalized_content = _normalize_space(content).casefold()
    normalized_snippet = _normalize_space(snippet).casefold()
    return normalized_snippet in normalized_content


def _normalize_space(value: str) -> str:
    return " ".join(value.split())


def _trim_text(value: str, limit: int) -> str:
    text = _normalize_space(value)
    if len(text) <= limit:
        return text
    trimmed = text[: limit - 3].rstrip()
    return f"{trimmed}..."
