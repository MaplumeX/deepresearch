from __future__ import annotations

import hashlib
import re

from app.domain.models import AcquiredContent, SourceDocument


def _extract_main_text(raw_content: str, content_format: str) -> str:
    if content_format in {"text", "markdown"}:
        return " ".join(raw_content.split())

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


def extract_sources(contents: list[AcquiredContent]) -> list[SourceDocument]:
    sources: list[SourceDocument] = []

    for item in contents:
        content = _extract_main_text(item.content, item.content_format)
        if not content:
            continue

        source_id = _make_source_id(item.url)
        sources.append(
            SourceDocument(
                source_id=source_id,
                url=item.url,
                title=item.title or item.url,
                content=content,
                fetched_at=item.acquired_at,
                providers=list(item.providers),
                acquisition_method=item.acquisition_method,
                metadata={
                    **item.metadata,
                    "content_format": item.content_format,
                },
            )
        )

    return sources
