from __future__ import annotations

from typing import Any

from app.config import Settings
from app.domain.models import ResearchPlan, ResearchTask
from app.services.conversation_memory import build_contextual_brief, format_memory_for_prompt
from app.services.llm import build_chat_model, can_use_llm


def _fallback_topics(gaps: list[str]) -> list[str]:
    if gaps:
        return [f"Resolve gap: {gap}" for gap in gaps]
    return [
        "Establish scope and terminology",
        "Collect recent evidence from credible sources",
        "Synthesize tradeoffs, uncertainties, and implications",
    ]


def _build_fallback_plan(
    question: str,
    gaps: list[str],
    max_tasks: int,
    memory: dict[str, Any] | None,
) -> list[ResearchTask]:
    tasks: list[ResearchTask] = []
    contextual_question = _with_memory_context(question, memory)
    for index, topic in enumerate(_fallback_topics(gaps)[:max_tasks], start=1):
        tasks.append(
            ResearchTask(
                task_id=f"task-{index}",
                title=topic,
                question=f"{contextual_question}\nFocus: {topic}",
            )
        )
    return tasks


def _maybe_plan_with_llm(
    question: str,
    gaps: list[str],
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
    memory: dict[str, Any] | None = None,
) -> list[ResearchTask]:
    planned = _maybe_plan_with_llm(question, gaps, max_tasks, settings, memory)
    if planned:
        return planned
    return _build_fallback_plan(question, gaps, max_tasks, memory)


def _with_memory_context(question: str, memory: dict[str, Any] | None) -> str:
    context = build_contextual_brief(memory, max_chars=260)
    if not context:
        return question
    return f"{question}\nConversation context:\n{context}"
