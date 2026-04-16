from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from app.domain.models import AcquiredContent, ResearchQuery, ResearchRequest, ResearchTask, SearchHit, SourceDocument
from app.config import get_settings
from app.runtime_progress import emit_progress
from app.services.research_quality import build_task_outcome
from app.services.research_progress import build_counts, build_progress_payload, build_task_progress
from app.services.research_worker import (
    build_task_evidence,
    filter_acquired_contents,
    rank_search_hits,
    rewrite_queries,
    select_hits_for_fetch_budget,
    select_queries_for_budget,
)
from app.services.source_content import replace_contents, should_escalate_to_firecrawl, should_escalate_to_jina_reader
from app.tools.extract import extract_sources
from app.tools.fetch import acquire_contents, fetch_with_firecrawl, fetch_with_jina_reader
from app.tools.search import search_web


class ResearchWorkerState(TypedDict, total=False):
    request: dict
    task: dict
    task_index: int
    task_total: int
    iteration_count: int
    queries: list[dict]
    executed_queries: list[str]
    search_hits: list[dict]
    fetch_urls: list[str]
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


def _emit_worker_progress(
    state: ResearchWorkerState,
    config: RunnableConfig | None,
    *,
    worker_step: str,
    message: str,
    search_hits: int | None = None,
    acquired_contents: int | None = None,
    kept_sources: int | None = None,
    evidence_count: int | None = None,
) -> None:
    request = _request_from_state(state)
    emit_progress(
        config,
        {
            "message": message,
            "progress": build_progress_payload(
                "executing_tasks",
                iteration=state.get("iteration_count"),
                max_iterations=request.max_iterations,
                task=build_task_progress(
                    state.get("task"),
                    index=state.get("task_index"),
                    total=state.get("task_total"),
                    status="running",
                    worker_step=worker_step,
                ),
                counts=build_counts(
                    planned_tasks=state.get("task_total"),
                    search_hits=search_hits,
                    acquired_contents=acquired_contents,
                    kept_sources=kept_sources,
                    evidence_count=evidence_count,
                ),
            ).model_dump(),
        },
    )


def rewrite_queries_node(state: ResearchWorkerState, config: RunnableConfig | None = None) -> dict:
    _emit_worker_progress(state, config, worker_step="rewrite_queries", message="Rewriting search queries for the current task.")
    task = _task_from_state(state)
    request = _request_from_state(state)
    settings = get_settings()
    return {"queries": [item.model_dump() for item in rewrite_queries(task, request, settings=settings)]}


async def search_and_rank_node(state: ResearchWorkerState, config: RunnableConfig | None = None) -> dict:
    _emit_worker_progress(state, config, worker_step="search_and_rank", message="Searching the web and ranking candidate sources.")
    task = _task_from_state(state)
    query_plan = [ResearchQuery.model_validate(item) for item in state.get("queries", [])]
    selected_queries = select_queries_for_budget(query_plan, budget=task.query_budget)
    settings = get_settings()
    candidate_limit = max(10, settings.search_max_results * 3)
    hits = await search_web([item.query for item in selected_queries], max_results=candidate_limit)
    ranked_hits = rank_search_hits(task, hits, limit=candidate_limit)
    return {
        "executed_queries": [item.query for item in selected_queries],
        "search_hits": [hit.model_dump() for hit in ranked_hits],
    }


async def acquire_and_filter_node(state: ResearchWorkerState, config: RunnableConfig | None = None) -> dict:
    _emit_worker_progress(
        state,
        config,
        worker_step="acquire_and_filter",
        message="Fetching and filtering source contents.",
        search_hits=len(state.get("search_hits", [])),
    )
    task = _task_from_state(state)
    settings = get_settings()
    ranked_hits = [SearchHit.model_validate(item) for item in state.get("search_hits", [])]
    hits = select_hits_for_fetch_budget(ranked_hits, budget=task.fetch_budget)
    acquired_contents = await acquire_contents(hits)
    if settings.enable_jina_reader_fallback:
        jina_candidates = [item for item in acquired_contents if should_escalate_to_jina_reader(item)]
        acquired_contents = replace_contents(
            acquired_contents,
            await fetch_with_jina_reader(jina_candidates, settings=settings),
        )
    if settings.enable_firecrawl_fallback:
        firecrawl_candidates = [item for item in acquired_contents if should_escalate_to_firecrawl(item)]
        acquired_contents = replace_contents(
            acquired_contents,
            await fetch_with_firecrawl(firecrawl_candidates, settings=settings),
        )
    filtered_limit = min(6, max(2, settings.search_max_results + 2))
    filtered_contents = filter_acquired_contents(task, acquired_contents, limit=filtered_limit)
    return {
        "fetch_urls": [hit.url for hit in hits],
        "acquired_contents": [item.model_dump() for item in filtered_contents],
    }


def extract_and_score_node(state: ResearchWorkerState, config: RunnableConfig | None = None) -> dict:
    _emit_worker_progress(
        state,
        config,
        worker_step="extract_and_score",
        message="Extracting evidence and scoring sources.",
        search_hits=len(state.get("search_hits", [])),
        acquired_contents=len(state.get("acquired_contents", [])),
    )
    task = _task_from_state(state)
    settings = get_settings()
    contents = [AcquiredContent.model_validate(item) for item in state.get("acquired_contents", [])]
    sources = extract_sources(contents)
    findings, kept_sources = build_task_evidence(task, sources, settings=settings)
    return {
        "sources": [source.model_dump() for source in kept_sources],
        "findings": [finding.model_dump() for finding in findings],
    }


def emit_results_node(state: ResearchWorkerState, config: RunnableConfig | None = None) -> dict:
    _emit_worker_progress(
        state,
        config,
        worker_step="emit_results",
        message="Emitting normalized task results.",
        search_hits=len(state.get("search_hits", [])),
        acquired_contents=len(state.get("acquired_contents", [])),
        kept_sources=len(state.get("sources", [])),
        evidence_count=len(state.get("findings", [])),
    )
    task = _task_from_state(state)
    query_plan = [ResearchQuery.model_validate(item) for item in state.get("queries", [])]
    executed_queries = [str(item) for item in state.get("executed_queries", []) if str(item).strip()]
    search_hits = [SearchHit.model_validate(item) for item in state.get("search_hits", [])]
    acquired_contents = [AcquiredContent.model_validate(item) for item in state.get("acquired_contents", [])]
    findings = list(state.get("findings", []))
    sources = [SourceDocument.model_validate(item) for item in state.get("sources", [])]
    stage_status = {
        "rewrite_queries": "ok" if query_plan else "failed",
        "search_and_rank": "ok" if search_hits else "failed",
        "acquire_and_filter": "ok" if acquired_contents else "failed",
        "extract_and_score": "ok" if (findings or sources) else "failed",
        "emit_results": "ok",
    }
    task_outcome = build_task_outcome(
        task,
        query_count=len(executed_queries),
        total_query_count=len(query_plan),
        search_hit_count=len(search_hits),
        acquired_content_count=len(acquired_contents),
        kept_source_count=len(sources),
        evidence_count=len(findings),
        source_urls=[source.url for source in sources],
        executed_queries=executed_queries,
        used_urls=[str(url) for url in state.get("fetch_urls", []) if str(url).strip()],
        stage_status=stage_status,
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


async def research_worker(state: dict, config: RunnableConfig | None = None) -> dict:
    result = await _RESEARCH_WORKER_GRAPH.ainvoke(
        {
            "request": state["request"],
            "task": state["task"],
            "task_index": state.get("task_index"),
            "task_total": state.get("task_total"),
            "iteration_count": state.get("iteration_count"),
        },
        config=config,
    )
    return {
        "raw_findings": result.get("raw_findings", []),
        "raw_source_batches": result.get("raw_source_batches", []),
        "task_outcomes": result.get("task_outcomes", []),
    }
