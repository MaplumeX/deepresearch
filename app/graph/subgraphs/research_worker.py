from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.domain.models import AcquiredContent, ResearchRequest, ResearchTask, SearchHit, SourceDocument
from app.config import get_settings
from app.services.research_quality import build_task_outcome
from app.services.research_worker import build_task_evidence, filter_acquired_contents, rank_search_hits, rewrite_queries
from app.tools.extract import extract_sources
from app.tools.fetch import acquire_contents
from app.tools.search import search_web


class ResearchWorkerState(TypedDict, total=False):
    request: dict
    task: dict
    queries: list[str]
    search_hits: list[dict]
    acquired_contents: list[dict]
    sources: list[dict]
    findings: list[dict]
    raw_findings: list[dict]
    raw_source_batches: list[dict[str, dict]]
    task_outcomes: list[dict]


def _task_from_state(state: ResearchWorkerState) -> ResearchTask:
    return ResearchTask.model_validate(state["task"])


def _request_from_state(state: ResearchWorkerState) -> ResearchRequest:
    return ResearchRequest.model_validate(state["request"])


def rewrite_queries_node(state: ResearchWorkerState) -> dict:
    task = _task_from_state(state)
    request = _request_from_state(state)
    return {"queries": rewrite_queries(task, request)}


async def search_and_rank_node(state: ResearchWorkerState) -> dict:
    task = _task_from_state(state)
    queries = state.get("queries", [])
    settings = get_settings()
    candidate_limit = max(5, settings.search_max_results * 2)
    hits = await search_web(queries, max_results=candidate_limit)
    ranked_hits = rank_search_hits(task, hits, limit=candidate_limit)
    return {"search_hits": [hit.model_dump() for hit in ranked_hits]}


async def acquire_and_filter_node(state: ResearchWorkerState) -> dict:
    task = _task_from_state(state)
    settings = get_settings()
    hits = [SearchHit.model_validate(item) for item in state.get("search_hits", [])]
    acquired_contents = await acquire_contents(hits)
    filtered_contents = filter_acquired_contents(task, acquired_contents, limit=max(1, settings.search_max_results))
    return {"acquired_contents": [item.model_dump() for item in filtered_contents]}


def extract_and_score_node(state: ResearchWorkerState) -> dict:
    task = _task_from_state(state)
    contents = [AcquiredContent.model_validate(item) for item in state.get("acquired_contents", [])]
    sources = extract_sources(contents)
    findings, kept_sources = build_task_evidence(task, sources)
    return {
        "sources": [source.model_dump() for source in kept_sources],
        "findings": [finding.model_dump() for finding in findings],
    }


def emit_results_node(state: ResearchWorkerState) -> dict:
    task = _task_from_state(state)
    queries = list(state.get("queries", []))
    search_hits = [SearchHit.model_validate(item) for item in state.get("search_hits", [])]
    acquired_contents = [AcquiredContent.model_validate(item) for item in state.get("acquired_contents", [])]
    findings = list(state.get("findings", []))
    sources = [SourceDocument.model_validate(item) for item in state.get("sources", [])]
    task_outcome = build_task_outcome(
        task,
        query_count=len(queries),
        search_hit_count=len(search_hits),
        acquired_content_count=len(acquired_contents),
        kept_source_count=len(sources),
        evidence_count=len(findings),
        source_urls=[source.url for source in sources],
    )
    if not findings and not sources:
        return {
            "raw_findings": [],
            "raw_source_batches": [],
            "task_outcomes": [task_outcome.model_dump()],
        }
    return {
        "raw_findings": findings,
        "raw_source_batches": [
            {source.source_id: source.model_dump() for source in sources}
        ],
        "task_outcomes": [task_outcome.model_dump()],
    }


def build_research_worker_graph():
    builder = StateGraph(ResearchWorkerState)
    builder.add_node("rewrite_queries", rewrite_queries_node)
    builder.add_node("search_and_rank", search_and_rank_node)
    builder.add_node("acquire_and_filter", acquire_and_filter_node)
    builder.add_node("extract_and_score", extract_and_score_node)
    builder.add_node("emit_results", emit_results_node)

    builder.add_edge(START, "rewrite_queries")
    builder.add_edge("rewrite_queries", "search_and_rank")
    builder.add_edge("search_and_rank", "acquire_and_filter")
    builder.add_edge("acquire_and_filter", "extract_and_score")
    builder.add_edge("extract_and_score", "emit_results")
    builder.add_edge("emit_results", END)
    return builder.compile()


_RESEARCH_WORKER_GRAPH = build_research_worker_graph()


async def research_worker(state: dict) -> dict:
    result = await _RESEARCH_WORKER_GRAPH.ainvoke(
        {
            "request": state["request"],
            "task": state["task"],
        }
    )
    return {
        "raw_findings": result.get("raw_findings", []),
        "raw_source_batches": result.get("raw_source_batches", []),
        "task_outcomes": result.get("task_outcomes", []),
    }
