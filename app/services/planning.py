from __future__ import annotations

from typing import Any

from app.config import Settings
from app.domain.models import ResearchGap, ResearchPlan, ResearchTask
from app.services.conversation_memory import build_contextual_brief, format_memory_for_prompt
from app.services.llm import build_chat_model, can_use_llm
from app.services.research_quality import format_gaps_for_prompt, normalize_gaps, sort_gaps


def _fallback_topics(gaps: list[ResearchGap]) -> list[ResearchGap]:
    if gaps:
        return sort_gaps(gaps)
    return []


def _build_fallback_plan(
    question: str,
    gaps: list[ResearchGap],
    max_tasks: int,
    memory: dict[str, Any] | None,
) -> list[ResearchTask]:
    tasks: list[ResearchTask] = []
    contextual_question = _with_memory_context(question, memory)
    sorted_gaps = _fallback_topics(gaps)
    if not sorted_gaps:
        sorted_gaps = [
            ResearchGap(
                gap_type="weak_evidence",
                task_id=f"seed-{index}",
                title=topic,
                reason=topic,
                retry_hint=topic,
                severity="medium",
            )
            for index, topic in enumerate(
                [
                    "Establish scope and terminology",
                    "Collect recent evidence from credible sources",
                    "Synthesize tradeoffs, uncertainties, and implications",
                ],
                start=1,
            )
        ]
    for index, gap in enumerate(sorted_gaps[:max_tasks], start=1):
        tasks.append(
            ResearchTask(
                task_id=f"task-{index}",
                title=gap.title,
                question=(
                    f"{contextual_question}\n"
                    f"Focus: {gap.title}\n"
                    f"Why this follow-up is needed: {gap.reason}\n"
                    f"Retry hint: {gap.retry_hint}"
                ),
            )
        )
    return tasks


def _maybe_plan_with_llm(
    question: str,
    gaps: list[ResearchGap],
    max_tasks: int,
    settings: Settings,
    memory: dict[str, Any] | None,
) -> list[ResearchTask] | None:
    if not settings.enable_llm_planning or not can_use_llm(settings):
        return None

    try:
        from langchain_core.output_parsers import PydanticOutputParser
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError:
        return None

    parser = PydanticOutputParser(pydantic_object=ResearchPlan)
    memory_sections = format_memory_for_prompt(memory)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are planning research tasks for a deep research workflow. "
                "Use conversation memory only for continuity, intent resolution, and terminology reuse. "
                "Conversation memory is not verified evidence. "
                "If memory conflicts with the new user request, prefer the new user request. "
                "Return at most {max_tasks} focused tasks.",
            ),
            (
                "human",
                "Current question:\n{question}\n\n"
                "Rolling summary from older turns:\n{rolling_summary}\n\n"
                "Recent 5 turns:\n{recent_turns}\n\n"
                "Known facts from older turns:\n{key_facts}\n\n"
                "Open questions from older turns:\n{open_questions}\n\n"
                "Open gaps in the current run:\n{gaps}\n\n"
                "{format_instructions}",
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
            "rolling_summary": memory_sections["rolling_summary"],
            "recent_turns": memory_sections["recent_turns"],
            "key_facts": memory_sections["key_facts"],
            "open_questions": memory_sections["open_questions"],
            "gaps": format_gaps_for_prompt(gaps),
            "max_tasks": max_tasks,
            "format_instructions": parser.get_format_instructions(),
        }
    )
    return response.tasks[:max_tasks]


def plan_research_tasks(
    question: str,
    gaps: list[dict[str, Any]] | list[ResearchGap] | list[str],
    max_tasks: int,
    settings: Settings,
    memory: dict[str, Any] | None = None,
) -> list[ResearchTask]:
    normalized_gaps = normalize_gaps(list(gaps))
    planned = _maybe_plan_with_llm(question, normalized_gaps, max_tasks, settings, memory)
    if planned:
        return planned
    return _build_fallback_plan(question, normalized_gaps, max_tasks, memory)


def _with_memory_context(question: str, memory: dict[str, Any] | None) -> str:
    context = build_contextual_brief(memory, max_chars=260)
    if not context:
        return question
    return f"{question}\nConversation context:\n{context}"
