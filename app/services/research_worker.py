from __future__ import annotations

import re
from urllib.parse import urlparse

from app.domain.models import AcquiredContent, Evidence, ResearchRequest, ResearchTask, SearchHit, SourceDocument


_QUERY_LIMIT = 3
_MIN_PAGE_CHARS = 200
_MIN_PAGE_SCORE = 0.12
_MIN_SNIPPET_CHARS = 80
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
    merged_hits = _merge_search_hits(hits)
    scored_hits = [
        (_score_search_hit(hit, keywords), index, hit)
        for index, hit in enumerate(merged_hits)
    ]
    scored_hits.sort(key=lambda item: (-item[0], item[1]))

    ranked = [hit for _, _, hit in scored_hits]
    if not ranked:
        return merged_hits[:limit]
    return _apply_host_diversity(ranked, limit)


def filter_acquired_contents(task: ResearchTask, contents: list[AcquiredContent], limit: int) -> list[AcquiredContent]:
    if not contents or limit <= 0:
        return []

    keywords = _keywords_for_task(task)
    scored_contents: list[tuple[float, int, AcquiredContent]] = []

    for index, item in enumerate(contents):
        content = _normalize_space(item.content)
        min_chars = _MIN_SNIPPET_CHARS if item.acquisition_method == "search_snippet" else _MIN_PAGE_CHARS
        if len(content) < min_chars:
            continue

        content_score = _score_acquired_content(
            title=item.title,
            content=content,
            keywords=keywords,
            acquisition_method=item.acquisition_method,
            provider_count=len(item.providers),
        )
        min_score = 0.08 if item.acquisition_method == "search_snippet" else _MIN_PAGE_SCORE
        if content_score < min_score:
            continue

        scored_contents.append((content_score, index, item))

    scored_contents.sort(key=lambda item: (-item[0], item[1]))
    if scored_contents:
        return [item for _, _, item in scored_contents[:limit]]

    return contents[:1]


def build_task_evidence(task: ResearchTask, sources: list[SourceDocument]) -> tuple[list[Evidence], list[SourceDocument]]:
    keywords = _keywords_for_task(task)
    findings: list[Evidence] = []
    kept_sources: list[SourceDocument] = []

    for index, source in enumerate(sources, start=1):
        snippet = _pick_best_snippet(source.content, keywords)
        if not snippet:
            continue

        relevance = _score_relevance(source.title, snippet, source.content, keywords)
        confidence = _score_confidence(snippet, source.content, source.acquisition_method)
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
    snippet_length_bonus = min(len(snippet_text) / 400, 1.0) * 0.08
    provider_bonus = min(len(hit.providers), 3) * 0.08
    raw_content_bonus = 0.08 if hit.raw_content else 0.0
    rank_bonus = _provider_rank_bonus(hit)
    return round((title_overlap * 0.5) + (snippet_overlap * 0.22) + snippet_length_bonus + provider_bonus + raw_content_bonus + rank_bonus, 4)


def _score_acquired_content(
    title: str,
    content: str,
    keywords: set[str],
    acquisition_method: str,
    provider_count: int,
) -> float:
    title_overlap = _keyword_overlap_ratio(keywords, title)
    content_overlap = _keyword_overlap_ratio(keywords, content[:4000])
    length_bonus = min(len(content) / 5000, 1.0) * 0.15
    acquisition_bonus = {
        "provider_raw_content": 0.12,
        "http_fetch": 0.08,
        "search_snippet": 0.02,
    }.get(acquisition_method, 0.0)
    provider_bonus = min(provider_count, 3) * 0.03
    return round((title_overlap * 0.38) + (content_overlap * 0.34) + length_bonus + acquisition_bonus + provider_bonus, 4)


def _score_relevance(title: str, snippet: str, content: str, keywords: set[str]) -> float:
    title_overlap = _keyword_overlap_ratio(keywords, title)
    snippet_overlap = _keyword_overlap_ratio(keywords, snippet)
    content_overlap = _keyword_overlap_ratio(keywords, content[:4000])
    score = 0.3 + (title_overlap * 0.25) + (snippet_overlap * 0.3) + (content_overlap * 0.15)
    return round(_clamp(score, 0.0, 1.0), 2)


def _score_confidence(snippet: str, content: str, acquisition_method: str) -> float:
    length_bonus = min(len(content) / 6000, 1.0) * 0.2
    evidence_signal = 0.15 if re.search(r"\d", snippet) else 0.0
    sentence_bonus = 0.15 if len(snippet) >= 80 else 0.05
    acquisition_bonus = {
        "provider_raw_content": 0.1,
        "http_fetch": 0.07,
        "search_snippet": -0.05,
    }.get(acquisition_method, 0.0)
    score = 0.3 + length_bonus + evidence_signal + sentence_bonus + acquisition_bonus
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


def _merge_search_hits(hits: list[SearchHit]) -> list[SearchHit]:
    grouped: dict[str, list[SearchHit]] = {}
    ordered_urls: list[str] = []
    for hit in hits:
        if not hit.url:
            continue
        if hit.url not in grouped:
            grouped[hit.url] = []
            ordered_urls.append(hit.url)
        grouped[hit.url].append(hit)
    return [_merge_search_hit_group(grouped[url]) for url in ordered_urls]


def _merge_search_hit_group(hits: list[SearchHit]) -> SearchHit:
    primary = hits[0].model_copy(deep=True)
    primary.title = _longest_non_empty(hit.title for hit in hits) or primary.url
    primary.snippet = _longest_non_empty(hit.snippet for hit in hits)
    providers = sorted({provider for hit in hits for provider in hit.providers})
    provider_metadata: dict[str, dict] = {}
    for hit in hits:
        for provider, metadata in hit.provider_metadata.items():
            provider_metadata[provider] = dict(metadata)
    raw_hit = max((hit for hit in hits if hit.raw_content), key=lambda item: len(item.raw_content or ""), default=None)
    primary.providers = providers
    primary.provider_metadata = provider_metadata
    primary.raw_content = raw_hit.raw_content if raw_hit else None
    primary.raw_content_format = raw_hit.raw_content_format if raw_hit else None
    return primary


def _apply_host_diversity(hits: list[SearchHit], limit: int) -> list[SearchHit]:
    selected: list[SearchHit] = []
    deferred: list[SearchHit] = []
    seen_hosts: set[str] = set()

    for hit in hits:
        host = _hostname(hit.url)
        if host and host not in seen_hosts:
            selected.append(hit)
            seen_hosts.add(host)
        else:
            deferred.append(hit)
        if len(selected) >= limit:
            return selected[:limit]

    for hit in deferred:
        selected.append(hit)
        if len(selected) >= limit:
            break
    return selected[:limit]


def _provider_rank_bonus(hit: SearchHit) -> float:
    ranks = [
        metadata.get("rank")
        for metadata in hit.provider_metadata.values()
        if isinstance(metadata.get("rank"), int)
    ]
    if not ranks:
        return 0.0
    best_rank = min(ranks)
    return max(0.0, 0.12 - ((best_rank - 1) * 0.015))


def _hostname(url: str) -> str:
    return urlparse(url).netloc.casefold()


def _longest_non_empty(values) -> str:
    normalized = [_normalize_space(value) for value in values if _normalize_space(value)]
    if not normalized:
        return ""
    return max(normalized, key=len)


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
