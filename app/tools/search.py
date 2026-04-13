from __future__ import annotations

from app.config import get_settings
from app.domain.models import SearchHit


async def search_web(queries: list[str]) -> list[SearchHit]:
    settings = get_settings()
    if not settings.tavily_api_key:
        return []

    try:
        from tavily import TavilyClient
    except ImportError:
        return []

    client = TavilyClient(api_key=settings.tavily_api_key)
    hits_by_url: dict[str, SearchHit] = {}

    for query in queries:
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=settings.search_max_results,
        )
        for item in response.get("results", []):
            hit = SearchHit(
                title=item.get("title", item.get("url", "")),
                url=item.get("url", ""),
                snippet=item.get("content", "") or "",
            )
            if hit.url and hit.url not in hits_by_url:
                hits_by_url[hit.url] = hit

    return list(hits_by_url.values())

