from __future__ import annotations

from typing import Any

from app.config import Settings
from app.domain.models import CoverageRequirement, ResearchGap, ResearchPlan, ResearchTask
from app.services.conversation_memory import build_contextual_brief, format_memory_for_prompt
from app.services.llm import build_structured_chat_model, can_use_llm
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
                coverage_tags=_coverage_tags_for_gap(gap),
            )
        )
    return tasks


def _maybe_plan_with_llm(
    question: str,
    gaps: list[ResearchGap],
    max_tasks: int,
    settings: Settings,
    memory: dict[str, Any] | None,
) -> ResearchPlan | None:
    if not settings.enable_llm_planning or not can_use_llm(settings):
        return None

    try:
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError:
        return None

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
        return None

    chain = prompt | model
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
    return ResearchPlan(
        tasks=[
            task.model_copy(update={"coverage_tags": _finalize_coverage_tags(task.coverage_tags)})
            for task in response.tasks[:max_tasks]
        ],
        coverage_requirements=_finalize_coverage_requirements(response.coverage_requirements),
    )


def plan_research_tasks(
    question: str,
    gaps: list[dict[str, Any]] | list[ResearchGap] | list[str],
    max_tasks: int,
    settings: Settings,
    memory: dict[str, Any] | None = None,
) -> ResearchPlan:
    normalized_gaps = normalize_gaps(list(gaps))
    planned = _maybe_plan_with_llm(question, normalized_gaps, max_tasks, settings, memory)
    if planned:
        return planned
    return ResearchPlan(
        tasks=_build_fallback_plan(question, normalized_gaps, max_tasks, memory),
        coverage_requirements=_build_default_coverage_requirements(),
    )


def _with_memory_context(question: str, memory: dict[str, Any] | None) -> str:
    context = build_contextual_brief(memory, max_chars=260)
    if not context:
        return question
    return f"{question}\nConversation context:\n{context}"


def _build_default_coverage_requirements() -> list[CoverageRequirement]:
    return [
        CoverageRequirement(
            requirement_id="scope-terminology",
            title="Scope and terminology",
            description="Clarify what the question covers, key terms, and the decision context.",
            coverage_tags=["scope", "definitions"],
        ),
        CoverageRequirement(
            requirement_id="recent-evidence",
            title="Recent evidence and concrete examples",
            description="Ground the answer in recent, corroborated evidence and concrete examples or measurable data.",
            coverage_tags=["recent", "evidence", "examples"],
        ),
        CoverageRequirement(
            requirement_id="risks-tradeoffs",
            title="Risks, tradeoffs, and implications",
            description="Explain limitations, risks, tradeoffs, or downstream implications of the answer.",
            coverage_tags=["risks", "tradeoffs"],
        ),
    ]


def _coverage_tags_for_gap(gap: ResearchGap) -> list[str]:
    title = gap.title.casefold()
    tags: list[str] = []

    if "scope" in title or "terminology" in title:
        tags.extend(["scope", "definitions"])
    if "recent" in title or "2025" in title or "2026" in title:
        tags.extend(["recent", "evidence"])
    if any(token in title for token in ("example", "case", "benchmark", "data")):
        tags.extend(["examples", "evidence"])
    if any(token in title for token in ("risk", "limitation", "tradeoff", "implication")):
        tags.extend(["risks", "tradeoffs"])

    if gap.gap_type in {"retrieval_failure", "missing_evidence", "weak_evidence", "low_source_diversity"}:
        tags.append("evidence")
    if gap.gap_type == "coverage_gap" and not tags:
        tags.extend(["recent", "examples", "risks"])

    return _finalize_coverage_tags(tags)


def _finalize_coverage_tags(tags: list[str]) -> list[str]:
    finalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        normalized = " ".join(str(tag).split()).strip().casefold()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        finalized.append(normalized)
    if not finalized:
        return ["evidence"]
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
        seen.add(requirement_id)
        finalized.append(
            requirement.model_copy(
                update={
                    "requirement_id": requirement_id,
                    "coverage_tags": _finalize_coverage_tags(requirement.coverage_tags),
                }
            )
        )
    if finalized:
        return finalized
    return _build_default_coverage_requirements()
