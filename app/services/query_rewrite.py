from __future__ import annotations

from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.domain.models import QueryIntent, ResearchQuery, ResearchRequest, ResearchTask
from app.services.llm import (
    LLMInvocationError,
    LLMOutputInvalidError,
    build_structured_chat_model,
    ensure_planning_llm_ready,
)


_QUERY_LIMIT = 6
_MIN_QUERY_COUNT = 3
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
    ensure_planning_llm_ready(effective_settings)

    planned = _rewrite_queries_with_llm(task, request, effective_settings)
    queries = _dedupe_queries(planned)[:_QUERY_LIMIT]
    if len(queries) < _MIN_QUERY_COUNT:
        raise LLMOutputInvalidError(
            f"Query rewrite returned {len(queries)} distinct queries; expected at least {_MIN_QUERY_COUNT}.",
        )
    return queries


def _rewrite_queries_with_llm(
    task: ResearchTask,
    request: ResearchRequest,
    settings: Settings,
) -> list[ResearchQuery]:
    try:
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError as exc:
        raise LLMInvocationError("Query rewrite dependencies are not installed.") from exc

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
        raise LLMInvocationError("Query rewrite model could not be initialized.")

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
    except Exception as exc:
        raise LLMInvocationError("Query rewrite failed.") from exc

    return [
        ResearchQuery(
            query=item.query,
            intent=item.intent,
            priority=_INTENT_PRIORITY[item.intent],
        )
        for item in response.queries
    ]


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


def _normalize_space(value: str) -> str:
    return " ".join(value.split())
