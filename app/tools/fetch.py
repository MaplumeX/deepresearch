from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.config import Settings, get_settings
from app.domain.models import AcquiredContent, SearchHit
from app.tools.extract import build_extraction_metadata


_MIN_PROVIDER_RAW_CHARS = 200
_JINA_READER_BASE_URL = "https://r.jina.ai/"
_FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v1/scrape"
_REQUEST_HEADERS = {
    "User-Agent": "deepresearch-agent/0.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.7",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
}


def _fetch_with_urllib(hit: SearchHit, timeout: float) -> AcquiredContent | None:
    request = Request(
        hit.url,
        headers=_REQUEST_HEADERS,
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            content = response.read().decode("utf-8", errors="ignore")
            content_type = response.headers.get("Content-Type", "")
            final_url = response.geturl()
    except Exception:
        return None
    content_format = _content_format_from_content_type(content_type)
    metadata = {
        "provider_metadata": hit.provider_metadata,
        "content_type": content_type,
        "response_url": final_url,
        **build_extraction_metadata(content, content_format),
    }
    return AcquiredContent(
        url=hit.url,
        title=hit.title,
        content=content,
        content_format=content_format,
        acquired_at=_now_iso(),
        providers=list(hit.providers),
        acquisition_method="http_fetch",
        metadata=metadata,
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
        headers=_REQUEST_HEADERS,
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
        content_type = response.headers.get("content-type", "")
        content_format = _content_format_from_content_type(content_type)
        metadata = {
            "provider_metadata": hit.provider_metadata,
            "content_type": content_type,
            "response_url": str(response.url),
            "status_code": response.status_code,
            **build_extraction_metadata(response.text, content_format),
        }
        acquired[hit.url] = AcquiredContent(
            url=hit.url,
            title=hit.title,
            content=response.text,
            content_format=content_format,
            acquired_at=_now_iso(),
            providers=list(hit.providers),
            acquisition_method="http_fetch",
            metadata=metadata,
        )
    return _fill_snippet_fallbacks(unique_hits, acquired)


async def fetch_with_jina_reader(
    contents: list[AcquiredContent],
    *,
    settings: Settings | None = None,
) -> dict[str, AcquiredContent]:
    if not contents:
        return {}

    current_settings = settings or get_settings()
    if not current_settings.enable_jina_reader_fallback:
        return {}

    try:
        import httpx
    except ImportError:
        return {}

    async with httpx.AsyncClient(timeout=current_settings.jina_timeout_seconds, follow_redirects=True) as client:
        tasks = [_request_jina_reader(client, item, current_settings) for item in contents]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    upgraded: dict[str, AcquiredContent] = {}
    for response in responses:
        if isinstance(response, AcquiredContent):
            upgraded[response.url] = response
    return upgraded


async def fetch_with_firecrawl(
    contents: list[AcquiredContent],
    *,
    settings: Settings | None = None,
) -> dict[str, AcquiredContent]:
    if not contents:
        return {}

    current_settings = settings or get_settings()
    if not current_settings.enable_firecrawl_fallback or not current_settings.firecrawl_api_key:
        return {}

    try:
        import httpx
    except ImportError:
        return {}

    async with httpx.AsyncClient(timeout=current_settings.firecrawl_timeout_seconds, follow_redirects=True) as client:
        tasks = [_request_firecrawl_scrape(client, item, current_settings) for item in contents]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

    upgraded: dict[str, AcquiredContent] = {}
    for response in responses:
        if isinstance(response, AcquiredContent):
            upgraded[response.url] = response
    return upgraded


def _provider_raw_content_candidate(hit: SearchHit) -> AcquiredContent | None:
    raw_content = _normalize_space(hit.raw_content or "")
    if len(raw_content) < _MIN_PROVIDER_RAW_CHARS:
        return None
    content_format = hit.raw_content_format or "text"
    return AcquiredContent(
        url=hit.url,
        title=hit.title,
        content=raw_content,
        content_format=content_format,
        acquired_at=_now_iso(),
        providers=list(hit.providers),
        acquisition_method="provider_raw_content",
        metadata={
            "provider_metadata": hit.provider_metadata,
            **build_extraction_metadata(raw_content, content_format),
        },
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


def _content_format_from_content_type(content_type: str) -> str:
    lowered = content_type.casefold()
    if "markdown" in lowered:
        return "markdown"
    if "text/plain" in lowered:
        return "text"
    return "html"


async def _request_jina_reader(client, item: AcquiredContent, settings: Settings) -> AcquiredContent | None:
    headers = {"Accept": "text/plain"}
    if settings.jina_api_key:
        headers["Authorization"] = f"Bearer {settings.jina_api_key}"

    response = await client.get(_jina_reader_url(item.url), headers=headers)
    try:
        response.raise_for_status()
    except Exception:
        return None

    content = response.text.strip()
    if not content:
        return None

    metadata = {
        **item.metadata,
        "fallback_provider": "jina_reader",
        "fallback_source_method": item.acquisition_method,
        "fallback_reason": item.metadata.get("quality_failure_reason"),
        "provider_metadata": item.metadata.get("provider_metadata", {}),
        "response_url": str(response.url),
        "content_type": response.headers.get("content-type", ""),
        **build_extraction_metadata(content, "markdown"),
    }
    return AcquiredContent(
        url=item.url,
        title=item.title,
        content=content,
        content_format="markdown",
        acquired_at=_now_iso(),
        providers=list(item.providers),
        acquisition_method="jina_reader",
        metadata=metadata,
    )


async def _request_firecrawl_scrape(client, item: AcquiredContent, settings: Settings) -> AcquiredContent | None:
    response = await client.post(
        _FIRECRAWL_SCRAPE_URL,
        headers={
            "Authorization": f"Bearer {settings.firecrawl_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "url": item.url,
            "formats": ["markdown", "html"],
            "onlyMainContent": True,
            "blockAds": True,
        },
    )
    try:
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return None

    if not payload.get("success", True):
        return None

    data = payload.get("data", payload)
    markdown = data.get("markdown")
    html = data.get("html") or data.get("rawHtml")
    content = markdown or html or ""
    if not isinstance(content, str) or not content.strip():
        return None

    content_format = "markdown" if isinstance(markdown, str) and markdown.strip() else "html"
    metadata = {
        **item.metadata,
        "fallback_provider": "firecrawl",
        "fallback_source_method": item.acquisition_method,
        "fallback_reason": item.metadata.get("quality_failure_reason"),
        "provider_metadata": item.metadata.get("provider_metadata", {}),
        "firecrawl_metadata": data.get("metadata", {}),
        "content_type": response.headers.get("content-type", ""),
        **build_extraction_metadata(content, content_format),
    }
    return AcquiredContent(
        url=item.url,
        title=_firecrawl_title(data, item.title),
        content=content,
        content_format=content_format,
        acquired_at=_now_iso(),
        providers=list(item.providers),
        acquisition_method="firecrawl_scrape",
        metadata=metadata,
    )


def _jina_reader_url(url: str) -> str:
    return f"{_JINA_READER_BASE_URL}{quote(url, safe='')}"


def _firecrawl_title(data: dict, fallback_title: str) -> str:
    metadata = data.get("metadata", {})
    title = metadata.get("title")
    if isinstance(title, str) and title.strip():
        return title.strip()
    return fallback_title
