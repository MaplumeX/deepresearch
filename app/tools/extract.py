from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime

from app.domain.models import SourceDocument


def _extract_main_text(raw_content: str) -> str:
    try:
        import trafilatura
    except ImportError:
        trafilatura = None

    if trafilatura is not None:
        extracted = trafilatura.extract(raw_content)
        if extracted:
            return " ".join(extracted.split())

    stripped = re.sub(r"<[^>]+>", " ", raw_content)
    return " ".join(stripped.split())


def _make_source_id(url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return f"S{digest}"


def extract_sources(pages: list[dict]) -> list[SourceDocument]:
    sources: list[SourceDocument] = []

    for page in pages:
        content = _extract_main_text(page.get("content", ""))
        if not content:
            continue

        source_id = _make_source_id(page["url"])
        sources.append(
            SourceDocument(
                source_id=source_id,
                url=page["url"],
                title=page.get("title", page["url"]),
                content=content,
                fetched_at=datetime.now(UTC).isoformat(),
            )
        )

    return sources
