from __future__ import annotations

import asyncio
import re
from typing import Any, Protocol

from app.config import get_settings
from app.domain.models import SearchHit


_HTML_TAG_PATTERN = re.compile(r"<[a-zA-Z][^>]*>")


class SearchProvider(Protocol):
    name: str

    async def search(self, queries: list[str], max_results: int) -> list[SearchHit]:
        ...


class TavilySearchProvider:
    name = "tavily"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(self, queries: list[str], max_results: int) -> list[SearchHit]:
        try:
            from tavily import TavilyClient
        except ImportError:
            return []

        client = TavilyClient(api_key=self._api_key)
        tasks = [
            asyncio.to_thread(
                client.search,
                query=query,
                search_depth="advanced",
                include_raw_content=True,
                max_results=max_results,
            )
            for query in queries
        ]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        hits: list[SearchHit] = []
        for query, response in zip(queries, responses):
            if isinstance(response, Exception):
                continue
            hits.extend(_normalize_tavily_results(response, query))
        return hits


class BraveSearchProvider:
    name = "brave"
    _SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search(self, queries: list[str], max_results: int) -> list[SearchHit]:
        try:
            import httpx
        except ImportError:
            return []

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            tasks = [
                client.get(
                    self._SEARCH_URL,
                    params={
                        "q": query,
                        "count": max_results,
                        "spellcheck": 0,
                    },
                    headers={
                        "Accept": "application/json",
                        "X-Subscription-Token": self._api_key,
                    },
                )
                for query in queries
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

        hits: list[SearchHit] = []
        for query, response in zip(queries, responses):
            if isinstance(response, Exception):
                continue
            try:
                response.raise_for_status()
                payload = response.json()
            except Exception:
                continue
            hits.extend(_normalize_brave_results(payload, query))
        return hits


class SerperSearchProvider:
    name = "serper"
    _SEARCH_URL = "https://google.serper.dev/search"

    def __init__(self, api_key: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search(self, queries: list[str], max_results: int) -> list[SearchHit]:
        try:
            import httpx
        except ImportError:
            return []

        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            tasks = [
                client.post(
                    self._SEARCH_URL,
                    headers={"X-API-KEY": self._api_key},
                    json={"q": query, "num": max_results},
                )
                for query in queries
            ]
            responses = await asyncio.gather(*tasks, return_exceptions=True)

        hits: list[SearchHit] = []
        for query, response in zip(queries, responses):
            if isinstance(response, Exception):
                continue
            try:
                response.raise_for_status()
                payload = response.json()
            except Exception:
                continue
            hits.extend(_normalize_serper_results(payload, query))
        return hits


async def search_web(queries: list[str], max_results: int) -> list[SearchHit]:
    settings = get_settings()
    providers = _build_providers(settings)
    if not queries or max_results <= 0 or not providers:
        return []

    responses = await asyncio.gather(
        *(provider.search(queries, max_results) for provider in providers),
        return_exceptions=True,
    )
    hits: list[SearchHit] = []
    for response in responses:
        if isinstance(response, Exception):
            continue
        hits.extend(response)
    return hits


def _build_providers(settings) -> list[SearchProvider]:
    providers: list[SearchProvider] = []
    if settings.tavily_api_key:
        providers.append(TavilySearchProvider(settings.tavily_api_key))
    if settings.brave_api_key:
        providers.append(BraveSearchProvider(settings.brave_api_key, settings.fetch_timeout_seconds))
    if settings.serper_api_key:
        providers.append(SerperSearchProvider(settings.serper_api_key, settings.fetch_timeout_seconds))
    return providers


def _normalize_tavily_results(response: dict[str, Any], query: str) -> list[SearchHit]:
    hits: list[SearchHit] = []
    for rank, item in enumerate(response.get("results", []), start=1):
        url = item.get("url", "")
        if not url:
            continue
        raw_content = item.get("raw_content")
        hits.append(
            SearchHit(
                title=item.get("title", url),
                url=url,
                snippet=item.get("content", "") or "",
                providers=["tavily"],
                provider_metadata={
                    "tavily": {
                        "query": query,
                        "rank": rank,
                        "score": item.get("score"),
                        "published_date": item.get("published_date"),
                    }
                },
                raw_content=raw_content or None,
                raw_content_format=_detect_content_format(raw_content) if raw_content else None,
            )
        )
    return hits


def _normalize_brave_results(payload: dict[str, Any], query: str) -> list[SearchHit]:
    web_results = payload.get("web", {}).get("results", [])
    hits: list[SearchHit] = []
    for rank, item in enumerate(web_results, start=1):
        url = item.get("url", "")
        if not url:
            continue
        snippet_parts = [item.get("description", "") or "", *(item.get("extra_snippets") or [])]
        snippet = " ".join(part.strip() for part in snippet_parts if part and part.strip())
        hits.append(
            SearchHit(
                title=item.get("title", url),
                url=url,
                snippet=snippet,
                providers=["brave"],
                provider_metadata={
                    "brave": {
                        "query": query,
                        "rank": rank,
                        "age": item.get("age"),
                        "language": item.get("language"),
                    }
                },
            )
        )
    return hits


def _normalize_serper_results(payload: dict[str, Any], query: str) -> list[SearchHit]:
    organic = payload.get("organic", [])
    hits: list[SearchHit] = []
    for rank, item in enumerate(organic, start=1):
        url = item.get("link", "")
        if not url:
            continue
        hits.append(
            SearchHit(
                title=item.get("title", url),
                url=url,
                snippet=item.get("snippet", "") or "",
                providers=["serper"],
                provider_metadata={
                    "serper": {
                        "query": query,
                        "rank": rank,
                        "site_links": item.get("siteLinks"),
                    }
                },
            )
        )
    return hits


def _detect_content_format(raw_content: Any) -> str:
    if not isinstance(raw_content, str):
        return "text"
    return "html" if _HTML_TAG_PATTERN.search(raw_content) else "text"
