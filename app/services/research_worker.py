from __future__ import annotations

import re

from app.domain.models import Evidence, ResearchRequest, ResearchTask, SearchHit, SourceDocument


_QUERY_LIMIT = 3
_MIN_PAGE_CHARS = 200
_MIN_PAGE_SCORE = 0.12
_MAX_SNIPPET_LENGTH = 280
_MAX_CLAIM_LENGTH = 220
_TOKEN_PATTERN = re.compile(r"[\u4e00-\u9fff]{2,}|[a-z0-9]{3,}", re.IGNORECASE)


def rewrite_queries(task: ResearchTask, request: ResearchRequest) -> list[str]:
    candidates = [
        task.question,
        f"{request.question} {task.title}",
    ]
    if request.scope:
        candidates.append(f"{task.question} {request.scope}")

    queries: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = _normalize_space(candidate)
        if not normalized:
            continue
        dedupe_key = normalized.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        queries.append(normalized)
        if len(queries) >= _QUERY_LIMIT:
            break
    return queries


def rank_search_hits(task: ResearchTask, hits: list[SearchHit], limit: int) -> list[SearchHit]:
    if not hits or limit <= 0:
        return []

    keywords = _keywords_for_task(task)
    scored_hits = [
        (_score_search_hit(hit, keywords), index, hit)
        for index, hit in enumerate(hits)
    ]
    scored_hits.sort(key=lambda item: (-item[0], item[1]))

    ranked = [hit for _, _, hit in scored_hits[:limit]]
    if ranked:
        return ranked
    return hits[:limit]


def filter_pages(task: ResearchTask, pages: list[dict], limit: int) -> list[dict]:
    if not pages or limit <= 0:
        return []

    keywords = _keywords_for_task(task)
    scored_pages: list[tuple[float, int, dict]] = []

    for index, page in enumerate(pages):
        content = _normalize_space(str(page.get("content", "")))
        if len(content) < _MIN_PAGE_CHARS:
            continue

        page_score = _score_page(
            title=str(page.get("title", "")),
            content=content,
            keywords=keywords,
        )
        if page_score < _MIN_PAGE_SCORE:
            continue

        scored_pages.append((page_score, index, page))

    scored_pages.sort(key=lambda item: (-item[0], item[1]))
    if scored_pages:
        return [page for _, _, page in scored_pages[:limit]]

    return pages[:1]


def build_task_evidence(task: ResearchTask, sources: list[SourceDocument]) -> tuple[list[Evidence], list[SourceDocument]]:
    keywords = _keywords_for_task(task)
    findings: list[Evidence] = []
    kept_sources: list[SourceDocument] = []

    for index, source in enumerate(sources, start=1):
        snippet = _pick_best_snippet(source.content, keywords)
        if not snippet:
            continue

        relevance = _score_relevance(source.title, snippet, source.content, keywords)
        confidence = _score_confidence(snippet, source.content)
        if relevance < 0.2:
            continue

        kept_sources.append(source)
        findings.append(
            Evidence(
                evidence_id=f"{task.task_id}-evidence-{index}",
                task_id=task.task_id,
                claim=_build_claim(source.title, snippet),
                snippet=snippet,
                source_id=source.source_id,
                url=source.url,
                title=source.title,
                relevance_score=relevance,
                confidence=confidence,
            )
        )

    return findings, kept_sources


def _score_search_hit(hit: SearchHit, keywords: set[str]) -> float:
    title_text = _normalize_space(f"{hit.title} {hit.url}")
    snippet_text = _normalize_space(hit.snippet)
    title_overlap = _keyword_overlap_ratio(keywords, title_text)
    snippet_overlap = _keyword_overlap_ratio(keywords, snippet_text)
    snippet_length_bonus = min(len(snippet_text) / 400, 1.0) * 0.1
    return round((title_overlap * 0.65) + (snippet_overlap * 0.25) + snippet_length_bonus, 4)


def _score_page(title: str, content: str, keywords: set[str]) -> float:
    title_overlap = _keyword_overlap_ratio(keywords, title)
    content_overlap = _keyword_overlap_ratio(keywords, content[:4000])
    length_bonus = min(len(content) / 5000, 1.0) * 0.15
    return round((title_overlap * 0.45) + (content_overlap * 0.4) + length_bonus, 4)


def _score_relevance(title: str, snippet: str, content: str, keywords: set[str]) -> float:
    title_overlap = _keyword_overlap_ratio(keywords, title)
    snippet_overlap = _keyword_overlap_ratio(keywords, snippet)
    content_overlap = _keyword_overlap_ratio(keywords, content[:4000])
    score = 0.3 + (title_overlap * 0.25) + (snippet_overlap * 0.3) + (content_overlap * 0.15)
    return round(_clamp(score, 0.0, 1.0), 2)


def _score_confidence(snippet: str, content: str) -> float:
    length_bonus = min(len(content) / 6000, 1.0) * 0.2
    evidence_signal = 0.15 if re.search(r"\d", snippet) else 0.0
    sentence_bonus = 0.15 if len(snippet) >= 80 else 0.05
    score = 0.3 + length_bonus + evidence_signal + sentence_bonus
    return round(_clamp(score, 0.0, 1.0), 2)


def _build_claim(title: str, snippet: str) -> str:
    sentence = _trim_text(snippet, _MAX_CLAIM_LENGTH)
    if sentence:
        return sentence
    return _trim_text(title, _MAX_CLAIM_LENGTH)


def _pick_best_snippet(content: str, keywords: set[str]) -> str:
    sentences = _split_sentences(content)
    if not sentences:
        return _trim_text(_normalize_space(content), _MAX_SNIPPET_LENGTH)

    ranked = sorted(
        (
            (_score_sentence(sentence, keywords), index, sentence)
            for index, sentence in enumerate(sentences)
        ),
        key=lambda item: (-item[0], item[1]),
    )
    best = ranked[0][2] if ranked else ""
    return _trim_text(best, _MAX_SNIPPET_LENGTH)


def _score_sentence(sentence: str, keywords: set[str]) -> float:
    overlap = _keyword_overlap_ratio(keywords, sentence)
    length_bonus = min(len(sentence) / 200, 1.0) * 0.15
    evidence_signal = 0.1 if re.search(r"\d", sentence) else 0.0
    return overlap + length_bonus + evidence_signal


def _split_sentences(content: str) -> list[str]:
    normalized = _normalize_space(content)
    if not normalized:
        return []
    parts = re.split(r"(?<=[。！？.!?])\s+|\n+", normalized)
    return [part.strip() for part in parts if part.strip()]


def _keywords_for_task(task: ResearchTask) -> set[str]:
    return set(_TOKEN_PATTERN.findall(f"{task.title} {task.question}".casefold()))


def _keyword_overlap_ratio(keywords: set[str], text: str) -> float:
    if not keywords:
        return 0.0
    text_tokens = set(_TOKEN_PATTERN.findall(text.casefold()))
    if not text_tokens:
        return 0.0
    overlap = len(keywords & text_tokens)
    return overlap / len(keywords)


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
