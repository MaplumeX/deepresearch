from __future__ import annotations

import re
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.domain.models import Evidence, EvidenceType, ResearchTask, SourceDocument, SourceRole
from app.services.llm import build_structured_chat_model, can_use_llm


_MAX_EVIDENCE_PER_SOURCE = 3
_MAX_SNIPPET_LENGTH = 280
_MAX_CLAIM_LENGTH = 220
_MAX_CANDIDATE_SNIPPETS = 12
_TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,}|[a-z0-9]{3,}", re.IGNORECASE)
_DIGIT_PATTERN = re.compile(r"\d")
_EXAMPLE_PATTERN = re.compile(r"\b(example|case|customer|deployment|study)\b|案例|示例|实践", re.IGNORECASE)
_RISK_PATTERN = re.compile(r"\b(risk|failure|problem|issue|challenge)\b|风险|问题|失败|挑战", re.IGNORECASE)
_LIMITATION_PATTERN = re.compile(r"\b(limit|limitation|constraint|caveat)\b|局限|限制|前提", re.IGNORECASE)
_TREND_PATTERN = re.compile(r"\b(trend|forecast|outlook|roadmap)\b|趋势|展望|路线图", re.IGNORECASE)
_COMPARISON_PATTERN = re.compile(r"\b(compare|comparison|versus|vs|tradeoff)\b|对比|差异|取舍", re.IGNORECASE)
_DEFINITION_PATTERN = re.compile(r"\b(is|refers to|defined as)\b|是指|定义为|指的是", re.IGNORECASE)
_COMMENTARY_HOST_PATTERN = re.compile(r"(blog|medium|substack|newsletter|opinion)")


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
    llm_items = _maybe_extract_source_evidence_with_llm(task, source, settings)
    fallback_items = _extract_evidence_fallback(task, source)
    merged = _merge_evidence_items(llm_items, fallback_items)
    return [
        item.model_copy(update={"evidence_id": f"{task.task_id}-{item.source_id}-{index}"})
        for index, item in enumerate(merged, start=1)
    ]


def _maybe_extract_source_evidence_with_llm(
    task: ResearchTask,
    source: SourceDocument,
    settings: Settings,
) -> list[Evidence]:
    if not settings.enable_llm_synthesis or not can_use_llm(settings):
        return []

    try:
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError:
        return []

    candidate_snippets = _pick_candidate_snippets(source.content, _keywords_for_task(task), limit=_MAX_CANDIDATE_SNIPPETS)
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
        return []

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
    except Exception:
        return []

    validated: list[Evidence] = []
    for item in response.items:
        evidence = _validate_evidence_draft(task, source, item)
        if evidence is None:
            continue
        validated.append(evidence)
    return validated[:_MAX_EVIDENCE_PER_SOURCE]


def _extract_evidence_fallback(task: ResearchTask, source: SourceDocument) -> list[Evidence]:
    keywords = _keywords_for_task(task)
    source_role = _infer_source_role(source)
    findings: list[Evidence] = []

    for index, snippet in enumerate(
        _pick_candidate_snippets(source.content, keywords, limit=_MAX_EVIDENCE_PER_SOURCE),
        start=1,
    ):
        relevance = _score_relevance(source.title, snippet, source.content, keywords)
        if relevance < 0.2:
            continue
        findings.append(
            Evidence(
                evidence_id=f"{task.task_id}-{source.source_id}-fallback-{index}",
                task_id=task.task_id,
                claim=_build_claim(source.title, snippet),
                snippet=snippet,
                source_id=source.source_id,
                url=source.url,
                title=source.title,
                evidence_type=_classify_evidence_type(snippet),
                source_role=source_role,
                relevance_score=relevance,
                confidence=_score_confidence(snippet, source.content, source.acquisition_method),
            )
        )
    return findings


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

    relevance = _score_relevance(source.title, snippet, source.content, _keywords_for_task(task))
    if relevance < 0.2:
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
        relevance_score=relevance,
        confidence=_score_confidence(snippet, source.content, source.acquisition_method),
    )


def _merge_evidence_items(primary: list[Evidence], fallback: list[Evidence]) -> list[Evidence]:
    merged: list[Evidence] = []
    seen_keys: set[tuple[str, str]] = set()
    for item in [*primary, *fallback]:
        key = (_normalize_space(item.claim).casefold(), _normalize_space(item.snippet).casefold())
        if not key[0] and not key[1]:
            continue
        if key in seen_keys:
            continue
        seen_keys.add(key)
        merged.append(item)
        if len(merged) >= _MAX_EVIDENCE_PER_SOURCE:
            break
    return merged


def _pick_candidate_snippets(content: str, keywords: set[str], *, limit: int) -> list[str]:
    sentences = _split_sentences(content)
    if not sentences:
        fallback = _trim_text(_normalize_space(content), _MAX_SNIPPET_LENGTH)
        return [fallback] if fallback else []

    ranked = sorted(
        (
            (_score_sentence(sentence, keywords), index, _trim_text(sentence, _MAX_SNIPPET_LENGTH))
            for index, sentence in enumerate(sentences)
        ),
        key=lambda item: (-item[0], item[1]),
    )
    snippets: list[str] = []
    seen: set[str] = set()
    for _, _, snippet in ranked:
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


def _score_relevance(title: str, snippet: str, content: str, keywords: set[str]) -> float:
    title_overlap = _keyword_overlap_ratio(keywords, title)
    snippet_overlap = _keyword_overlap_ratio(keywords, snippet)
    content_overlap = _keyword_overlap_ratio(keywords, content[:4000])
    score = 0.3 + (title_overlap * 0.25) + (snippet_overlap * 0.3) + (content_overlap * 0.15)
    return round(_clamp(score, 0.0, 1.0), 2)


def _score_confidence(snippet: str, content: str, acquisition_method: str) -> float:
    length_bonus = min(len(content) / 6000, 1.0) * 0.2
    evidence_signal = 0.15 if _DIGIT_PATTERN.search(snippet) else 0.0
    sentence_bonus = 0.15 if len(snippet) >= 80 else 0.05
    acquisition_bonus = {
        "provider_raw_content": 0.1,
        "http_fetch": 0.07,
        "jina_reader": 0.08,
        "firecrawl_scrape": 0.09,
        "search_snippet": -0.05,
    }.get(acquisition_method, 0.0)
    score = 0.3 + length_bonus + evidence_signal + sentence_bonus + acquisition_bonus
    return round(_clamp(score, 0.0, 1.0), 2)


def _classify_evidence_type(snippet: str) -> EvidenceType:
    if _RISK_PATTERN.search(snippet):
        return "risk"
    if _LIMITATION_PATTERN.search(snippet):
        return "limitation"
    if _EXAMPLE_PATTERN.search(snippet):
        return "example"
    if _COMPARISON_PATTERN.search(snippet):
        return "comparison"
    if _TREND_PATTERN.search(snippet):
        return "trend"
    if _DEFINITION_PATTERN.search(snippet):
        return "definition"
    if _DIGIT_PATTERN.search(snippet):
        return "statistic"
    return "fact"


def _infer_source_role(source: SourceDocument) -> SourceRole:
    host = (urlparse(source.url).hostname or "").casefold()
    if host.endswith(".gov") or host.endswith(".edu") or host.startswith("docs.") or "developer." in host:
        return "official"
    if _COMMENTARY_HOST_PATTERN.search(host):
        return "commentary"
    if "doi.org" in host or "arxiv.org" in host:
        return "primary"
    return "secondary"


def _build_claim(title: str, snippet: str) -> str:
    sentence = _trim_text(snippet, _MAX_CLAIM_LENGTH)
    if sentence:
        return sentence
    return _trim_text(title, _MAX_CLAIM_LENGTH)


def _keywords_for_task(task: ResearchTask) -> set[str]:
    return set(_TOKEN_PATTERN.findall(f"{task.title} {task.question}".casefold()))


def _score_sentence(sentence: str, keywords: set[str]) -> float:
    overlap = _keyword_overlap_ratio(keywords, sentence)
    length_bonus = min(len(sentence) / 200, 1.0) * 0.15
    evidence_signal = 0.1 if _DIGIT_PATTERN.search(sentence) else 0.0
    return overlap + length_bonus + evidence_signal


def _split_sentences(content: str) -> list[str]:
    normalized = _normalize_space(content)
    if not normalized:
        return []
    parts = re.split(r"(?<=[。！？.!?])\s+|\n+", normalized)
    return [part.strip() for part in parts if part.strip()]


def _keyword_overlap_ratio(keywords: set[str], text: str) -> float:
    if not keywords:
        return 0.0
    text_tokens = set(_TOKEN_PATTERN.findall(text.casefold()))
    if not text_tokens:
        return 0.0
    overlap = len(keywords & text_tokens)
    return overlap / len(keywords)


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


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))
