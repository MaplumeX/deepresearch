from __future__ import annotations

from app.domain.models import ResearchRequest, ResearchTask
from app.tools.extract import extract_evidence
from app.tools.fetch import fetch_pages
from app.tools.search import search_web


def _build_queries(task: ResearchTask, request: ResearchRequest) -> list[str]:
    queries = [task.question]
    if request.scope:
        queries.append(f"{task.question}\nScope: {request.scope}")
    return queries[:2]


async def research_worker(state: dict) -> dict:
    task = ResearchTask.model_validate(state["task"])
    request = ResearchRequest.model_validate(state["request"])
    search_hits = await search_web(_build_queries(task, request))
    pages = await fetch_pages(search_hits)
    findings, sources = extract_evidence(task, pages)
    if not findings and not sources:
        return {
            "raw_findings": [],
            "raw_source_batches": [],
        }
    return {
        "raw_findings": [finding.model_dump() for finding in findings],
        "raw_source_batches": [
            {source.source_id: source.model_dump() for source in sources}
        ],
    }

