from __future__ import annotations

import asyncio
from urllib.request import Request, urlopen

from app.config import get_settings
from app.domain.models import SearchHit


def _fetch_with_urllib(hit: SearchHit, timeout: float) -> dict | None:
    request = Request(
        hit.url,
        headers={"User-Agent": "deepresearch-agent/0.1"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            content = response.read().decode("utf-8", errors="ignore")
    except Exception:
        return None
    return {"url": hit.url, "title": hit.title, "content": content}


async def fetch_pages(hits: list[SearchHit]) -> list[dict]:
    if not hits:
        return []

    settings = get_settings()

    try:
        import httpx
    except ImportError:
        tasks = [
            asyncio.to_thread(_fetch_with_urllib, hit, settings.fetch_timeout_seconds)
            for hit in hits
        ]
        results = await asyncio.gather(*tasks)
        return [item for item in results if item]

    async with httpx.AsyncClient(
        timeout=settings.fetch_timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": "deepresearch-agent/0.1"},
    ) as client:
        pages: list[dict] = []
        for hit in hits:
            try:
                response = await client.get(hit.url)
                response.raise_for_status()
            except Exception:
                continue
            pages.append(
                {
                    "url": hit.url,
                    "title": hit.title,
                    "content": response.text,
                }
            )
    return pages

