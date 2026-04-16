from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.domain.models import QueryIntent, ResearchQuery, ResearchRequest, ResearchTask
from app.services.llm import build_structured_chat_model, can_use_llm


_QUERY_LIMIT = 6
_MIN_QUERY_COUNT = 3
_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")
_INTENT_PRIORITY: dict[QueryIntent, int] = {
    "official": 0,
    "recent": 1,
    "baseline": 2,
    "example": 3,
    "risk": 4,
    "comparison": 5,
}


class QueryRewriteDraft(BaseModel):
    query: str = Field(min_length=1)
    intent: QueryIntent


class QueryRewritePlan(BaseModel):
    queries: list[QueryRewriteDraft] = Field(default_factory=list)


def rewrite_queries(
    task: ResearchTask,
    request: ResearchRequest,
    settings: Settings | None = None,
) -> list[ResearchQuery]:
    effective_settings = settings or get_settings()
    fallback_queries = _rewrite_queries_fallback(task, request)
    planned = _maybe_rewrite_queries_with_llm(task, request, effective_settings)
    if planned is None:
        return fallback_queries
    return _finalize_queries(planned, fallback_queries)


def _rewrite_queries_fallback(task: ResearchTask, request: ResearchRequest) -> list[ResearchQuery]:
    base_question = _normalize_space(task.question)
    full_question = _normalize_space(request.question)
    combined = _normalize_space(f"{request.question} {task.title}")
    scope = _normalize_space(request.scope or "")
    localized_terms = _intent_terms(request)

    candidates = [
        _query_candidate(base_question, "baseline"),
        _query_candidate(f"{base_question} {localized_terms['official']}", "official"),
        _query_candidate(f"{base_question} {localized_terms['recent']}", "recent"),
        _query_candidate(f"{base_question} {localized_terms['example']}", "example"),
        _query_candidate(f"{base_question} {localized_terms['risk']}", "risk"),
        _query_candidate(f"{full_question} {localized_terms['comparison']}", "comparison"),
        _query_candidate(combined, "baseline", priority=6),
    ]
    if scope:
        candidates.append(_query_candidate(f"{base_question} {scope}", "baseline", priority=7))

    return _dedupe_queries(candidates)[:_QUERY_LIMIT]


def _maybe_rewrite_queries_with_llm(
    task: ResearchTask,
    request: ResearchRequest,
    settings: Settings,
) -> list[ResearchQuery] | None:
    if not settings.enable_llm_planning or not can_use_llm(settings):
        return None

    try:
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError:
        return None

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You rewrite research queries for a deep research worker. "
                "Return 4 to 6 distinct search queries that intentionally broaden coverage. "
                "Cover these intents once when relevant: baseline, official, recent, example, risk, comparison. "
                "Keep each query concise. Reuse the user's language. "
                "Do not explain your reasoning.",
            ),
            (
                "human",
                "Question:\n{question}\n\n"
                "Task title:\n{task_title}\n\n"
                "Task question:\n{task_question}\n\n"
                "Scope:\n{scope}\n\n"
                "Return only distinct queries with explicit intent labels.",
            ),
        ]
    )
    model = build_structured_chat_model(settings.planner_model, settings, QueryRewritePlan, temperature=0)
    if model is None:
        return None

    chain = prompt | model
    try:
        response: QueryRewritePlan = chain.invoke(
            {
                "question": request.question,
                "task_title": task.title,
                "task_question": task.question,
                "scope": request.scope or "None",
            }
        )
    except Exception:
        return None

    return [
        ResearchQuery(
            query=item.query,
            intent=item.intent,
            priority=_INTENT_PRIORITY[item.intent],
        )
        for item in response.queries
    ]


def _finalize_queries(
    planned: list[ResearchQuery],
    fallback_queries: list[ResearchQuery],
) -> list[ResearchQuery]:
    queries = _dedupe_queries(planned)[:_QUERY_LIMIT]
    if len(queries) >= _MIN_QUERY_COUNT:
        return queries

    seen = {query.query.casefold() for query in queries}
    combined = queries + [item for item in fallback_queries if item.query.casefold() not in seen]
    return combined[:_QUERY_LIMIT]


def _dedupe_queries(candidates: list[ResearchQuery]) -> list[ResearchQuery]:
    queries: list[ResearchQuery] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = _normalize_space(candidate.query)
        if not normalized:
            continue
        dedupe_key = normalized.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        queries.append(candidate.model_copy(update={"query": normalized}))
    queries.sort(key=lambda item: (item.priority, item.query.casefold()))
    return queries


def _query_candidate(query: str, intent: QueryIntent, *, priority: int | None = None) -> ResearchQuery:
    return ResearchQuery(
        query=query,
        intent=intent,
        priority=_INTENT_PRIORITY[intent] if priority is None else priority,
    )


def _intent_terms(request: ResearchRequest) -> dict[str, str]:
    if request.output_language == "zh-CN" or _CJK_PATTERN.search(f"{request.question} {request.scope or ''}"):
        return {
            "official": "官方 一手 规范 文档",
            "recent": "最新 2025 2026 现状",
            "example": "案例 数据 实践",
            "risk": "风险 局限 失败 问题",
            "comparison": "对比 差异 取舍",
        }
    return {
        "official": "official primary source documentation",
        "recent": "latest 2025 2026 current",
        "example": "case study examples data",
        "risk": "risks limitations failures",
        "comparison": "comparison tradeoffs alternatives",
    }


def _normalize_space(value: str) -> str:
    return " ".join(value.split())
