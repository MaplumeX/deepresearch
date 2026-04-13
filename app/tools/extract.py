from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime

from app.domain.models import Evidence, ResearchTask, SourceDocument


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


def extract_evidence(task: ResearchTask, pages: list[dict]) -> tuple[list[Evidence], list[SourceDocument]]:
    findings: list[Evidence] = []
    sources: list[SourceDocument] = []

    for index, page in enumerate(pages, start=1):
        content = _extract_main_text(page.get("content", ""))
        if not content:
            continue

        source_id = _make_source_id(page["url"])
        source = SourceDocument(
            source_id=source_id,
            url=page["url"],
            title=page.get("title", page["url"]),
            content=content,
            fetched_at=datetime.now(UTC).isoformat(),
        )
        evidence = Evidence(
            evidence_id=f"{task.task_id}-evidence-{index}",
            task_id=task.task_id,
            claim=f"{source.title} contains evidence relevant to {task.title.lower()}.",
            snippet=content[:400],
            source_id=source_id,
            url=source.url,
            title=source.title,
            relevance_score=0.6,
            confidence=0.4,
        )
        sources.append(source)
        findings.append(evidence)

    return findings, sources

