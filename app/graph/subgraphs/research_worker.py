from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.config import get_settings
from app.domain.models import ResearchRequest, ResearchTask, SearchHit, SourceDocument
from app.services.research_worker import build_task_evidence, filter_pages, rank_search_hits, rewrite_queries
from app.tools.extract import extract_sources
from app.tools.fetch import fetch_pages
from app.tools.search import search_web


class ResearchWorkerState(TypedDict, total=False):
    request: dict
    task: dict
    queries: list[str]
    search_hits: list[dict]
    pages: list[dict]
    sources: list[dict]
    findings: list[dict]
    raw_findings: list[dict]
    raw_source_batches: list[dict[str, dict]]


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
    hits = await search_web(queries)
    settings = get_settings()
    ranked_hits = rank_search_hits(task, hits, limit=max(1, settings.search_max_results))
    return {"search_hits": [hit.model_dump() for hit in ranked_hits]}


async def fetch_and_filter_node(state: ResearchWorkerState) -> dict:
    task = _task_from_state(state)
    settings = get_settings()
    hits = [SearchHit.model_validate(item) for item in state.get("search_hits", [])]
    pages = await fetch_pages(hits)
    filtered_pages = filter_pages(task, pages, limit=max(1, settings.search_max_results))
    return {"pages": filtered_pages}


def extract_and_score_node(state: ResearchWorkerState) -> dict:
    task = _task_from_state(state)
    sources = extract_sources(state.get("pages", []))
    findings, kept_sources = build_task_evidence(task, sources)
    return {
        "sources": [source.model_dump() for source in kept_sources],
        "findings": [finding.model_dump() for finding in findings],
    }


def emit_results_node(state: ResearchWorkerState) -> dict:
    findings = list(state.get("findings", []))
    sources = [SourceDocument.model_validate(item) for item in state.get("sources", [])]
    if not findings and not sources:
        return {
            "raw_findings": [],
            "raw_source_batches": [],
        }
    return {
        "raw_findings": findings,
        "raw_source_batches": [
            {source.source_id: source.model_dump() for source in sources}
        ],
    }


def build_research_worker_graph():
    builder = StateGraph(ResearchWorkerState)
    builder.add_node("rewrite_queries", rewrite_queries_node)
    builder.add_node("search_and_rank", search_and_rank_node)
    builder.add_node("fetch_and_filter", fetch_and_filter_node)
    builder.add_node("extract_and_score", extract_and_score_node)
    builder.add_node("emit_results", emit_results_node)

    builder.add_edge(START, "rewrite_queries")
    builder.add_edge("rewrite_queries", "search_and_rank")
    builder.add_edge("search_and_rank", "fetch_and_filter")
    builder.add_edge("fetch_and_filter", "extract_and_score")
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
    }
