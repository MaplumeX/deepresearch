from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from urllib.request import Request, urlopen

from app.config import get_settings
from app.domain.models import AcquiredContent, SearchHit


_MIN_PROVIDER_RAW_CHARS = 200


def _fetch_with_urllib(hit: SearchHit, timeout: float) -> AcquiredContent | None:
    request = Request(
        hit.url,
        headers={"User-Agent": "deepresearch-agent/0.1"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            content = response.read().decode("utf-8", errors="ignore")
    except Exception:
        return None
    return AcquiredContent(
        url=hit.url,
        title=hit.title,
        content=content,
        content_format="html",
        acquired_at=_now_iso(),
        providers=list(hit.providers),
        acquisition_method="http_fetch",
        metadata={"provider_metadata": hit.provider_metadata},
    )


async def acquire_contents(hits: list[SearchHit]) -> list[AcquiredContent]:
    if not hits:
        return []

    settings = get_settings()
    unique_hits = _unique_hits(hits)
    acquired: dict[str, AcquiredContent] = {}
    fetch_targets: list[SearchHit] = []

    for hit in unique_hits:
        provider_content = _provider_raw_content_candidate(hit)
        if provider_content is not None:
            acquired[hit.url] = provider_content
            continue
        fetch_targets.append(hit)

    try:
        import httpx
    except ImportError:
        tasks = [
            asyncio.to_thread(_fetch_with_urllib, hit, settings.fetch_timeout_seconds)
            for hit in fetch_targets
        ]
        results = await asyncio.gather(*tasks)
        for item in results:
            if item is not None:
                acquired[item.url] = item
        return _fill_snippet_fallbacks(unique_hits, acquired)

    async with httpx.AsyncClient(
        timeout=settings.fetch_timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": "deepresearch-agent/0.1"},
    ) as client:
        tasks = [client.get(hit.url) for hit in fetch_targets]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    for hit, response in zip(fetch_targets, responses):
        if isinstance(response, Exception):
            continue
        try:
            response.raise_for_status()
        except Exception:
            continue
        acquired[hit.url] = AcquiredContent(
            url=hit.url,
            title=hit.title,
            content=response.text,
            content_format="html",
            acquired_at=_now_iso(),
            providers=list(hit.providers),
            acquisition_method="http_fetch",
            metadata={"provider_metadata": hit.provider_metadata},
        )
    return _fill_snippet_fallbacks(unique_hits, acquired)


def _provider_raw_content_candidate(hit: SearchHit) -> AcquiredContent | None:
    raw_content = _normalize_space(hit.raw_content or "")
    if len(raw_content) < _MIN_PROVIDER_RAW_CHARS:
        return None
    return AcquiredContent(
        url=hit.url,
        title=hit.title,
        content=raw_content,
        content_format=hit.raw_content_format or "text",
        acquired_at=_now_iso(),
        providers=list(hit.providers),
        acquisition_method="provider_raw_content",
        metadata={"provider_metadata": hit.provider_metadata},
    )


def _snippet_fallback(hit: SearchHit) -> AcquiredContent | None:
    snippet = _normalize_space(hit.snippet)
    if not snippet:
        return None
    return AcquiredContent(
        url=hit.url,
        title=hit.title,
        content=snippet,
        content_format="text",
        acquired_at=_now_iso(),
        providers=list(hit.providers),
        acquisition_method="search_snippet",
        metadata={"provider_metadata": hit.provider_metadata},
    )


def _fill_snippet_fallbacks(hits: list[SearchHit], acquired: dict[str, AcquiredContent]) -> list[AcquiredContent]:
    for hit in hits:
        if hit.url in acquired:
            continue
        snippet = _snippet_fallback(hit)
        if snippet is not None:
            acquired[hit.url] = snippet
    return [acquired[hit.url] for hit in hits if hit.url in acquired]


def _unique_hits(hits: list[SearchHit]) -> list[SearchHit]:
    unique: list[SearchHit] = []
    seen: set[str] = set()
    for hit in hits:
        if not hit.url or hit.url in seen:
            continue
        seen.add(hit.url)
        unique.append(hit)
    return unique


def _normalize_space(value: str) -> str:
    return " ".join(value.split())


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()
