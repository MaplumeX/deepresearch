from __future__ import annotations

from typing import Any

from app.config import Settings
from app.domain.models import ResearchPlan, ResearchTask
from app.services.llm import build_chat_model, can_use_llm


def _fallback_topics(gaps: list[str]) -> list[str]:
    if gaps:
        return [f"Resolve gap: {gap}" for gap in gaps]
    return [
        "Establish scope and terminology",
        "Collect recent evidence from credible sources",
        "Synthesize tradeoffs, uncertainties, and implications",
    ]


def _build_fallback_plan(question: str, gaps: list[str], max_tasks: int) -> list[ResearchTask]:
    tasks: list[ResearchTask] = []
    for index, topic in enumerate(_fallback_topics(gaps)[:max_tasks], start=1):
        tasks.append(
            ResearchTask(
                task_id=f"task-{index}",
                title=topic,
                question=f"{question}\nFocus: {topic}",
            )
        )
    return tasks


def _maybe_plan_with_llm(
    question: str,
    gaps: list[str],
    max_tasks: int,
    settings: Settings,
) -> list[ResearchTask] | None:
    if not settings.enable_llm_planning or not can_use_llm(settings):
        return None

    try:
        from langchain_core.output_parsers import PydanticOutputParser
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError:
        return None

    parser = PydanticOutputParser(pydantic_object=ResearchPlan)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are planning research tasks for a deep research workflow. "
                "Return at most {max_tasks} focused tasks.",
            ),
            (
                "human",
                "Question:\n{question}\n\nOpen gaps:\n{gaps}\n\n{format_instructions}",
            ),
        ]
    )
    model = build_chat_model(settings.planner_model, settings, temperature=0)
    if model is None:
        return None

    chain = prompt | model | parser
    response: ResearchPlan = chain.invoke(
        {
            "question": question,
            "gaps": "\n".join(gaps) if gaps else "None",
            "max_tasks": max_tasks,
            "format_instructions": parser.get_format_instructions(),
        }
    )
    return response.tasks[:max_tasks]


def plan_research_tasks(
    question: str,
    gaps: list[str],
    max_tasks: int,
    settings: Settings,
) -> list[ResearchTask]:
    planned = _maybe_plan_with_llm(question, gaps, max_tasks, settings)
    if planned:
        return planned
    return _build_fallback_plan(question, gaps, max_tasks)
