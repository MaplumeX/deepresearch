from __future__ import annotations

from typing import Any

from app.config import Settings
from app.domain.models import CoverageRequirement, ResearchGap, ResearchPlan, ResearchTask
from app.services.conversation_memory import format_memory_for_prompt
from app.services.llm import (
    LLMInvocationError,
    LLMOutputInvalidError,
    build_structured_chat_model,
    ensure_planning_llm_ready,
)
from app.services.research_quality import format_gaps_for_prompt, normalize_gaps


def _plan_with_llm(
    question: str,
    gaps: list[ResearchGap],
    max_tasks: int,
    settings: Settings,
    memory: dict[str, Any] | None,
) -> ResearchPlan:
    ensure_planning_llm_ready(settings)

    try:
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError as exc:
        raise LLMInvocationError("Research planning dependencies are not installed.") from exc

    memory_sections = format_memory_for_prompt(memory)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You are planning research tasks for a deep research workflow. "
                "Use conversation memory only for continuity, intent resolution, and terminology reuse. "
                "Conversation memory is not verified evidence. "
                "If memory conflicts with the new user request, prefer the new user request. "
                "Return at most {max_tasks} focused tasks and a compact coverage rubric. "
                "Coverage requirements should describe what a complete answer must cover, not execution steps.",
            ),
            (
                "human",
                "Current question:\n{question}\n\n"
                "Rolling summary from older turns:\n{rolling_summary}\n\n"
                "Recent 5 turns:\n{recent_turns}\n\n"
                "Known facts from older turns:\n{key_facts}\n\n"
                "Open questions from older turns:\n{open_questions}\n\n"
                "Open gaps in the current run:\n{gaps}",
            ),
        ]
    )
    model = build_structured_chat_model(settings.planner_model, settings, ResearchPlan, temperature=0)
    if model is None:
        raise LLMInvocationError("Research planning model could not be initialized.")

    chain = prompt | model
    try:
        response: ResearchPlan = chain.invoke(
            {
                "question": question,
                "rolling_summary": memory_sections["rolling_summary"],
                "recent_turns": memory_sections["recent_turns"],
                "key_facts": memory_sections["key_facts"],
                "open_questions": memory_sections["open_questions"],
                "gaps": format_gaps_for_prompt(gaps),
                "max_tasks": max_tasks,
            }
        )
    except Exception as exc:
        raise LLMInvocationError("Research planning failed.") from exc

    tasks = _finalize_tasks(response.tasks[:max_tasks])
    coverage_requirements = _finalize_coverage_requirements(response.coverage_requirements)
    if not tasks:
        raise LLMOutputInvalidError("Research planning returned no tasks.")
    if not coverage_requirements:
        raise LLMOutputInvalidError("Research planning returned no coverage requirements.")
    return ResearchPlan(tasks=tasks, coverage_requirements=coverage_requirements)


def plan_research_tasks(
    question: str,
    gaps: list[dict[str, Any]] | list[ResearchGap] | list[str],
    max_tasks: int,
    settings: Settings,
    memory: dict[str, Any] | None = None,
) -> ResearchPlan:
    normalized_gaps = normalize_gaps(list(gaps))
    return _plan_with_llm(question, normalized_gaps, max_tasks, settings, memory)


def _finalize_tasks(tasks: list[ResearchTask]) -> list[ResearchTask]:
    finalized: list[ResearchTask] = []
    for index, task in enumerate(tasks, start=1):
        coverage_tags = _normalize_tags(task.coverage_tags)
        if not coverage_tags:
            raise LLMOutputInvalidError(
                f"Research planning returned task {index} without coverage tags.",
            )
        finalized.append(task.model_copy(update={"coverage_tags": coverage_tags}))
    return finalized


def _normalize_tags(tags: list[str]) -> list[str]:
    finalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        normalized = " ".join(str(tag).split()).strip().casefold()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        finalized.append(normalized)
    return finalized


def _finalize_coverage_requirements(
    requirements: list[CoverageRequirement],
) -> list[CoverageRequirement]:
    finalized: list[CoverageRequirement] = []
    seen: set[str] = set()
    for requirement in requirements:
        requirement_id = " ".join(requirement.requirement_id.split()).strip().casefold()
        if not requirement_id or requirement_id in seen:
            continue
        coverage_tags = _normalize_tags(requirement.coverage_tags)
        if not coverage_tags:
            raise LLMOutputInvalidError(
                f"Research planning returned coverage requirement `{requirement_id}` without coverage tags.",
            )
        seen.add(requirement_id)
        finalized.append(
            requirement.model_copy(
                update={
                    "requirement_id": requirement_id,
                    "coverage_tags": coverage_tags,
                }
            )
        )
    return finalized
