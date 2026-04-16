from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from app.config import Settings
from app.domain.models import CoverageRequirement, ReportDraft, ReportSectionDraft, StructuredReport
from app.services.conversation_memory import build_contextual_brief
from app.services.llm import (
    InsufficientEvidenceError,
    LLMInvocationError,
    LLMOutputInvalidError,
    LLMServiceError,
    build_structured_chat_model,
    ensure_synthesis_llm_ready,
)
from app.services.report_contract import ReportLabels, build_structured_report, get_report_labels
_MAX_TASK_TITLE_LENGTH = 120
_MAX_TASK_QUESTION_LENGTH = 220
_MAX_CLAIM_LENGTH = 280
_MAX_SNIPPET_LENGTH = 320
_MAX_SOURCE_TITLE_LENGTH = 140
_MAX_MEMORY_BRIEF_CHARS = 600
_MAX_REPORT_HEADING_LENGTH = 80


@dataclass(frozen=True, slots=True)
class CompactPayload:
    tasks: list[dict[str, Any]]
    coverage_requirements: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    sources: dict[str, dict[str, Any]]
    memory_brief: str
    estimated_size: int


@dataclass(frozen=True, slots=True)
class SectionPlan:
    heading: str
    purpose: str
    findings: list[dict[str, Any]]


class TaskReportHeadingDraft(BaseModel):
    task_id: str = Field(min_length=1)
    report_heading: str = Field(min_length=1)


class TaskReportHeadingPlan(BaseModel):
    tasks: list[TaskReportHeadingDraft] = Field(default_factory=list)


def assign_report_headings(
    question: str,
    tasks: list[dict],
    findings: list[dict],
    settings: Settings,
    output_language: str | None = None,
) -> list[dict]:
    if not tasks:
        return []

    ensure_synthesis_llm_ready(settings)
    labels = get_report_labels(output_language)
    drafted = _generate_report_headings_with_llm(
        question=question,
        tasks=tasks,
        findings=findings,
        settings=settings,
        labels=labels,
    )
    return _finalize_task_report_headings(tasks, drafted, labels)


def _maybe_synthesize_single_call(
    question: str,
    payload: CompactPayload,
    settings: Settings,
    labels: ReportLabels,
) -> ReportDraft:
    if not payload.findings:
        raise InsufficientEvidenceError("Synthesis requires evidence findings.")

    try:
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError as exc:
        raise LLMInvocationError("Synthesis dependencies are not installed.") from exc

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You synthesize structured cited reports from validated evidence. "
                "Background context is not a citation source. "
                "Keep all factual citations in the form [source_id]. "
                "Return analysis sections only. Do not include a sources appendix. "
                "Aim for comprehensive coverage while staying grounded in the supplied evidence.",
            ),
            (
                "human",
                "Current question:\n{question}\n\n"
                "Background brief:\n{memory_brief}\n\n"
                "Current tasks:\n{tasks}\n\n"
                "Coverage rubric:\n{coverage_requirements}\n\n"
                "Findings:\n{findings}\n\n"
                "Sources:\n{sources}\n\n"
                "Write a report-style synthesis. "
                "Write the report in {language_name}. "
                "Use the summary field for a concise cited summary under the heading '{summary_heading}'. "
                "If a coverage rubric is provided, prioritize rubric-based chapters in that order; otherwise prioritize task-based chapters using each task's report_heading as the chapter heading. "
                "Include '{risks_heading}' only when the evidence warrants it and the rubric does not already reserve a risk section, then finish with '{conclusion_heading}'. "
                "Do not include background, conversation context, or open questions sections. "
                "Use inline citations on factual claims.",
            ),
        ]
    )
    model = build_structured_chat_model(settings.synthesis_model, settings, ReportDraft, temperature=0)
    if model is None:
        raise LLMInvocationError("Synthesis model could not be initialized.")

    chain = prompt | model
    try:
        drafted: ReportDraft = chain.invoke(
            {
                "question": question,
                "memory_brief": payload.memory_brief,
                "tasks": payload.tasks,
                "coverage_requirements": payload.coverage_requirements,
                "findings": payload.findings,
                "sources": payload.sources,
                "language_name": labels.language_name,
                "summary_heading": labels.summary_heading,
                "risks_heading": labels.risks_heading,
                "conclusion_heading": labels.conclusion_heading,
            }
        )
    except Exception as exc:
        raise LLMInvocationError("Single-call synthesis failed.") from exc
    if not drafted.sections and payload.findings:
        raise LLMOutputInvalidError("Single-call synthesis returned no sections.")
    return drafted


def _maybe_synthesize_multi_stage(
    question: str,
    tasks: list[dict],
    coverage_requirements: list[dict] | None,
    findings: list[dict],
    sources: dict[str, dict],
    settings: Settings,
    memory_brief: str,
    labels: ReportLabels,
) -> ReportDraft:
    section_drafts: list[ReportSectionDraft] = []
    normalized_requirements = _normalize_coverage_requirements(coverage_requirements, labels)
    for plan in _build_section_plans(tasks, normalized_requirements, findings, labels):
        section_drafts.extend(
            _synthesize_section_plan(
                question=question,
                plan=plan,
                tasks=tasks,
                coverage_requirements=normalized_requirements,
                sources=sources,
                settings=settings,
                memory_brief=memory_brief,
                labels=labels,
            )
        )

    if not section_drafts:
        raise LLMOutputInvalidError("Multi-stage synthesis returned no sections.")
    return _merge_section_drafts(tasks, normalized_requirements, findings, section_drafts, labels)


def synthesize_report(
    question: str,
    tasks: list[dict],
    findings: list[dict],
    sources: dict[str, dict],
    settings: Settings,
    *,
    coverage_requirements: list[dict] | None = None,
    memory: dict[str, Any] | None = None,
    output_language: str | None = None,
) -> StructuredReport:
    ensure_synthesis_llm_ready(settings)
    if not findings:
        raise InsufficientEvidenceError("Synthesis requires evidence findings.")

    labels = get_report_labels(output_language)
    normalized_requirements = _normalize_coverage_requirements(coverage_requirements, labels)
    memory_brief = _build_synthesis_memory_brief(memory)
    payload = _build_compact_payload(
        question,
        tasks,
        normalized_requirements,
        findings,
        sources,
        memory_brief,
    )
    drafted: ReportDraft
    if _should_keep_payload_together(payload, settings):
        try:
            drafted = _maybe_synthesize_single_call(question, payload, settings, labels)
        except LLMServiceError:
            drafted = _maybe_synthesize_multi_stage(
                question,
                tasks,
                normalized_requirements,
                findings,
                sources,
                settings,
                memory_brief,
                labels,
            )
    else:
        drafted = _maybe_synthesize_multi_stage(
            question,
            tasks,
            normalized_requirements,
            findings,
            sources,
            settings,
            memory_brief,
            labels,
        )
    return build_structured_report(
        drafted,
        sources=sources,
        findings=findings,
        output_language=output_language,
    )


def _synthesize_section_plan(
    question: str,
    plan: SectionPlan,
    tasks: list[dict],
    coverage_requirements: list[dict[str, Any]],
    sources: dict[str, dict],
    settings: Settings,
    memory_brief: str,
    labels: ReportLabels,
    ) -> list[ReportSectionDraft]:
    relevant_tasks = _relevant_tasks(tasks, plan.findings)
    plan_payload = _build_compact_payload(
        question,
        relevant_tasks,
        coverage_requirements,
        plan.findings,
        sources,
        memory_brief,
        heading=plan.heading,
        purpose=plan.purpose,
        focus="Cross-task synthesis",
    )
    if _should_keep_payload_together(plan_payload, settings):
        try:
            draft = _maybe_synthesize_section_with_llm(
                question=question,
                plan=plan,
                payload=plan_payload,
                settings=settings,
                focus="Cross-task synthesis",
                labels=labels,
            )
            return [draft]
        except LLMServiceError:
            pass

    section_drafts: list[ReportSectionDraft] = []
    for task in relevant_tasks:
        task_findings = [item for item in plan.findings if item.get("task_id") == task.get("task_id")]
        for chunk in _chunk_findings_for_budget(
            question=question,
            tasks=[task],
            coverage_requirements=coverage_requirements,
            findings=task_findings,
            sources=sources,
            settings=settings,
            memory_brief=memory_brief,
            heading=plan.heading,
            purpose=plan.purpose,
            focus=_task_focus(task),
        ):
            payload = _build_compact_payload(
                question,
                [task],
                coverage_requirements,
                chunk,
                sources,
                memory_brief,
                heading=plan.heading,
                purpose=plan.purpose,
                focus=_task_focus(task),
            )
            if not _can_invoke_payload(payload.estimated_size, settings):
                raise LLMOutputInvalidError(
                    f"Synthesis payload for section `{plan.heading}` exceeded the hard limit.",
                )
            draft = _maybe_synthesize_section_with_llm(
                question=question,
                plan=plan,
                payload=payload,
                settings=settings,
                focus=_task_focus(task),
                labels=labels,
            )
            section_drafts.append(draft)

    if not section_drafts:
        raise LLMOutputInvalidError(f"Synthesis produced no valid sections for `{plan.heading}`.")
    return section_drafts


def _maybe_synthesize_section_with_llm(
    question: str,
    plan: SectionPlan,
    payload: CompactPayload,
    settings: Settings,
    focus: str,
    labels: ReportLabels,
) -> ReportSectionDraft:
    if not payload.findings:
        raise InsufficientEvidenceError(f"Synthesis section `{plan.heading}` requires evidence findings.")

    try:
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError as exc:
        raise LLMInvocationError("Section synthesis dependencies are not installed.") from exc

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You write one cited report section from validated evidence. "
                "Background context is not a citation source. "
                "Use inline citations in the form [source_id] for factual claims. "
                "Keep the section heading exactly as provided.",
            ),
            (
                "human",
                "Current question:\n{question}\n\n"
                "Background brief:\n{memory_brief}\n\n"
                "Section heading:\n{heading}\n\n"
                "Section purpose:\n{purpose}\n\n"
                "Current focus:\n{focus}\n\n"
                "Current tasks:\n{tasks}\n\n"
                "Findings:\n{findings}\n\n"
                "Sources:\n{sources}\n\n"
                "Write the section body in {language_name}. "
                "Return a single markdown section body for this heading only.",
            ),
        ]
    )
    model = build_structured_chat_model(settings.synthesis_model, settings, ReportSectionDraft, temperature=0)
    if model is None:
        raise LLMInvocationError("Section synthesis model could not be initialized.")

    chain = prompt | model
    try:
        drafted: ReportSectionDraft = chain.invoke(
            {
                "question": question,
                "memory_brief": payload.memory_brief,
                "heading": plan.heading,
                "purpose": plan.purpose,
                "focus": focus,
                "tasks": payload.tasks,
                "findings": payload.findings,
                "sources": payload.sources,
                "language_name": labels.language_name,
            }
        )
    except Exception as exc:
        raise LLMInvocationError(f"Section synthesis failed for `{plan.heading}`.") from exc
    body = drafted.body_markdown.strip()
    if not body:
        raise LLMOutputInvalidError(f"Section synthesis returned an empty body for `{plan.heading}`.")
    return ReportSectionDraft(heading=plan.heading, body_markdown=body)


def _merge_section_drafts(
    tasks: list[dict],
    coverage_requirements: list[dict[str, Any]],
    findings: list[dict],
    section_drafts: list[ReportSectionDraft],
    labels: ReportLabels,
) -> ReportDraft:
    grouped: dict[str, list[str]] = defaultdict(list)
    for draft in section_drafts:
        body = draft.body_markdown.strip()
        if not body:
            continue
        grouped[draft.heading].append(body)

    ordered_headings = _ordered_report_headings(tasks, coverage_requirements, grouped, labels)
    sections = [
        ReportSectionDraft(
            heading=heading,
            body_markdown=_merge_markdown_blocks(grouped[heading]),
        )
        for heading in ordered_headings
        if grouped.get(heading)
    ]
    if not sections:
        raise LLMOutputInvalidError("Merged synthesis sections produced no report content.")
    return ReportDraft(
        title=labels.title,
        summary="\n".join(_build_summary_lines(_primary_report_findings(findings), limit=3, labels=labels)),
        sections=sections,
    )


def _build_section_plans(
    tasks: list[dict],
    coverage_requirements: list[dict[str, Any]],
    findings: list[dict],
    labels: ReportLabels,
) -> list[SectionPlan]:
    plans = _build_requirement_section_plans(tasks, coverage_requirements, findings)
    if not plans:
        plans = _build_task_section_plans(tasks, findings)

    risks = [item for item in findings if _is_risk_finding(item)]
    if risks and not _has_risk_requirement(coverage_requirements):
        plans.append(
            SectionPlan(
                heading=labels.risks_heading,
                purpose="Explain the main risks, limitations, uncertainties, and failure modes in the evidence.",
                findings=risks,
            )
        )

    conclusion_findings = _primary_report_findings(findings)
    if conclusion_findings:
        plans.append(
            SectionPlan(
                heading=labels.conclusion_heading,
                purpose="Deliver a concise bottom-line synthesis grounded in the strongest validated evidence.",
                findings=conclusion_findings,
            )
        )

    return plans


def _build_summary_lines(findings: list[dict], limit: int, labels: ReportLabels) -> list[str]:
    summary_claims = _select_diverse_findings(_sort_findings_for_synthesis(findings), limit=limit)
    return [
        f"- {item['claim']} [{item['source_id']}]"
        for item in summary_claims
    ] or [labels.no_evidence_line]


def _should_keep_payload_together(payload: CompactPayload, settings: Settings) -> bool:
    return (
        bool(payload.findings)
        and len(payload.findings) <= settings.synthesis_max_findings_per_call
        and len(payload.sources) <= settings.synthesis_max_sources_per_call
        and payload.estimated_size <= settings.synthesis_soft_char_limit
    )


def _can_invoke_payload(estimated_size: int, settings: Settings) -> bool:
    return estimated_size <= settings.synthesis_hard_char_limit


def _chunk_findings_for_budget(
    question: str,
    tasks: list[dict],
    coverage_requirements: list[dict[str, Any]],
    findings: list[dict],
    sources: dict[str, dict],
    settings: Settings,
    memory_brief: str,
    heading: str,
    purpose: str,
    focus: str,
) -> list[list[dict]]:
    chunks: list[list[dict]] = []
    current: list[dict] = []
    for finding in _sort_findings_for_synthesis(findings):
        candidate = [*current, finding]
        payload = _build_compact_payload(
            question,
            tasks,
            coverage_requirements,
            candidate,
            sources,
            memory_brief,
            heading=heading,
            purpose=purpose,
            focus=focus,
        )
        if current and not _should_keep_payload_together(payload, settings):
            chunks.append(current)
            current = [finding]
            continue
        current = candidate
    if current:
        chunks.append(current)
    return chunks


def _build_compact_payload(
    question: str,
    tasks: list[dict],
    coverage_requirements: list[dict[str, Any]],
    findings: list[dict],
    sources: dict[str, dict],
    memory_brief: str,
    *,
    heading: str | None = None,
    purpose: str | None = None,
    focus: str | None = None,
) -> CompactPayload:
    compact_tasks = _build_compact_tasks(tasks)
    compact_requirements = _build_compact_coverage_requirements(coverage_requirements)
    compact_findings = _build_compact_findings(findings)
    compact_sources = _build_compact_sources(sources, compact_findings)
    estimated_size = _estimate_payload_size(
        question=question,
        tasks=compact_tasks,
        coverage_requirements=compact_requirements,
        findings=compact_findings,
        sources=compact_sources,
        memory_brief=memory_brief,
        heading=heading,
        purpose=purpose,
        focus=focus,
    )
    return CompactPayload(
        tasks=compact_tasks,
        coverage_requirements=compact_requirements,
        findings=compact_findings,
        sources=compact_sources,
        memory_brief=memory_brief,
        estimated_size=estimated_size,
    )


def _build_compact_tasks(tasks: list[dict]) -> list[dict[str, str]]:
    compact_tasks: list[dict[str, str]] = []
    for task in tasks:
        task_id = _as_text(task.get("task_id"))
        if not task_id:
            continue
        compact_tasks.append(
            {
                "task_id": task_id,
                "title": _trim_text(_as_text(task.get("title")), _MAX_TASK_TITLE_LENGTH) or task_id,
                "report_heading": _trim_text(_task_report_heading(task), _MAX_REPORT_HEADING_LENGTH),
                "question": _trim_text(_as_text(task.get("question")), _MAX_TASK_QUESTION_LENGTH),
            }
        )
    return compact_tasks


def _build_compact_coverage_requirements(
    coverage_requirements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    compact_requirements: list[dict[str, Any]] = []
    for requirement in coverage_requirements:
        requirement_id = _as_text(requirement.get("requirement_id"))
        heading = _trim_text(_as_text(requirement.get("heading")), _MAX_REPORT_HEADING_LENGTH)
        description = _trim_text(_as_text(requirement.get("description")), _MAX_TASK_QUESTION_LENGTH)
        if not requirement_id or not heading:
            continue
        compact_requirements.append(
            {
                "requirement_id": requirement_id,
                "heading": heading,
                "description": description,
                "coverage_tags": _as_string_list(requirement.get("coverage_tags")),
            }
        )
    return compact_requirements


def _build_compact_findings(findings: list[dict]) -> list[dict[str, Any]]:
    compact_findings: list[dict[str, Any]] = []
    for finding in _sort_findings_for_synthesis(findings):
        source_id = _as_text(finding.get("source_id"))
        claim = _trim_text(
            _as_text(finding.get("claim")) or _as_text(finding.get("snippet")),
            _MAX_CLAIM_LENGTH,
        )
        if not source_id or not claim:
            continue
        snippet = _trim_text(_as_text(finding.get("snippet")) or claim, _MAX_SNIPPET_LENGTH)
        compact_findings.append(
            {
                "task_id": _as_text(finding.get("task_id")),
                "source_id": source_id,
                "claim": claim,
                "snippet": snippet,
                "evidence_type": _as_text(finding.get("evidence_type")) or "fact",
                "source_role": _as_text(finding.get("source_role")) or "unknown",
                "confidence": _as_optional_float(finding.get("confidence")),
                "relevance_score": _as_optional_float(finding.get("relevance_score")),
                "title": _trim_text(_as_text(finding.get("title")), _MAX_SOURCE_TITLE_LENGTH),
                "url": _as_text(finding.get("url")),
            }
        )
    return compact_findings


def _build_compact_sources(
    sources: dict[str, dict],
    findings: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    ordered_source_ids: list[str] = []
    best_finding_by_source: dict[str, dict[str, Any]] = {}
    for finding in findings:
        source_id = _as_text(finding.get("source_id"))
        if not source_id:
            continue
        if source_id not in ordered_source_ids:
            ordered_source_ids.append(source_id)
        current = best_finding_by_source.get(source_id)
        if current is None or _finding_rank(finding) > _finding_rank(current):
            best_finding_by_source[source_id] = finding

    compact_sources: dict[str, dict[str, Any]] = {}
    for source_id in ordered_source_ids:
        source = sources.get(source_id, {})
        finding = best_finding_by_source.get(source_id, {})
        compact_sources[source_id] = {
            "source_id": source_id,
            "title": _trim_text(
                _as_text(source.get("title")) or _as_text(finding.get("title")) or source_id,
                _MAX_SOURCE_TITLE_LENGTH,
            ),
            "url": _as_text(source.get("url")) or _as_text(finding.get("url")),
            "snippet": _trim_text(
                _as_text(finding.get("snippet"))
                or _as_text(source.get("snippet"))
                or _as_text(source.get("content")),
                _MAX_SNIPPET_LENGTH,
            ),
            "providers": _as_string_list(source.get("providers")),
            "source_role": _as_text(finding.get("source_role")) or "unknown",
        }
    return compact_sources


def _estimate_payload_size(
    *,
    question: str,
    tasks: list[dict[str, Any]],
    coverage_requirements: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    sources: dict[str, dict[str, Any]],
    memory_brief: str,
    heading: str | None = None,
    purpose: str | None = None,
    focus: str | None = None,
) -> int:
    payload: dict[str, Any] = {
        "question": _trim_text(question, _MAX_TASK_QUESTION_LENGTH),
        "memory_brief": memory_brief,
        "tasks": tasks,
        "coverage_requirements": coverage_requirements,
        "findings": findings,
        "sources": sources,
    }
    if heading:
        payload["heading"] = heading
    if purpose:
        payload["purpose"] = purpose
    if focus:
        payload["focus"] = focus
    return len(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _build_synthesis_memory_brief(memory: dict[str, Any] | None) -> str:
    brief = build_contextual_brief(memory, max_chars=_MAX_MEMORY_BRIEF_CHARS)
    return brief or "None"


def _relevant_tasks(tasks: list[dict], findings: list[dict]) -> list[dict]:
    relevant_task_ids = {
        str(item.get("task_id", "")).strip()
        for item in findings
        if str(item.get("task_id", "")).strip()
    }
    relevant_tasks = [
        task for task in tasks if str(task.get("task_id", "")).strip() in relevant_task_ids
    ]
    return relevant_tasks or list(tasks)


def _task_focus(task: dict) -> str:
    title = _trim_text(_as_text(task.get("title")), _MAX_TASK_TITLE_LENGTH)
    question = _trim_text(_as_text(task.get("question")), _MAX_TASK_QUESTION_LENGTH)
    if title and question:
        return f"{title}: {question}"
    return title or question or "Task-focused synthesis"


def _merge_markdown_blocks(blocks: list[str]) -> str:
    merged: list[str] = []
    seen: set[str] = set()
    for block in blocks:
        normalized = _normalize_space(block)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        merged.append(block.strip())
    return "\n\n".join(merged)


def _build_task_section_plans(tasks: list[dict], findings: list[dict]) -> list[SectionPlan]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for finding in findings:
        task_id = _as_text(finding.get("task_id"))
        if not task_id or _is_risk_finding(finding):
            continue
        grouped[task_id].append(finding)

    plans: list[SectionPlan] = []
    for task in tasks:
        task_id = _as_text(task.get("task_id"))
        if not task_id:
            continue
        task_findings = grouped.get(task_id, [])
        if not task_findings:
            continue
        plans.append(
            SectionPlan(
                heading=_task_report_heading(task),
                purpose=_task_section_purpose(task),
                findings=task_findings,
            )
        )
    return plans


def _build_requirement_section_plans(
    tasks: list[dict],
    coverage_requirements: list[dict[str, Any]],
    findings: list[dict],
) -> list[SectionPlan]:
    plans: list[SectionPlan] = []
    for requirement in coverage_requirements:
        requirement_findings = _findings_for_requirement(tasks, requirement, findings)
        if not requirement_findings:
            continue
        plans.append(
            SectionPlan(
                heading=_coverage_requirement_heading(requirement),
                purpose=_coverage_requirement_purpose(requirement),
                findings=requirement_findings,
            )
        )
    return plans


def _ordered_report_headings(
    tasks: list[dict],
    coverage_requirements: list[dict[str, Any]],
    grouped_sections: dict[str, list[str]],
    labels: ReportLabels,
) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    for requirement in coverage_requirements:
        heading = _coverage_requirement_heading(requirement)
        if heading in grouped_sections and heading not in seen:
            seen.add(heading)
            ordered.append(heading)

    for task in tasks:
        heading = _task_report_heading(task)
        if heading in grouped_sections and heading not in seen:
            seen.add(heading)
            ordered.append(heading)

    for heading in (labels.risks_heading, labels.conclusion_heading):
        if heading in grouped_sections and heading not in seen:
            seen.add(heading)
            ordered.append(heading)

    for heading in grouped_sections:
        if heading in seen:
            continue
        ordered.append(heading)
    return ordered


def _primary_report_findings(findings: list[dict]) -> list[dict]:
    non_risk = [item for item in findings if not _is_risk_finding(item)]
    return non_risk or list(findings)


def _is_risk_finding(finding: dict[str, Any]) -> bool:
    return _as_text(finding.get("evidence_type")) in {"risk", "limitation"}


def _normalize_coverage_requirements(
    coverage_requirements: list[dict] | None,
    labels: ReportLabels,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in coverage_requirements or []:
        try:
            requirement = CoverageRequirement.model_validate(item)
        except Exception:
            continue
        requirement_id = _normalize_space(requirement.requirement_id).casefold()
        if not requirement_id or requirement_id in seen:
            continue
        seen.add(requirement_id)
        normalized.append(
            {
                "requirement_id": requirement_id,
                "title": _trim_text(requirement.title, _MAX_REPORT_HEADING_LENGTH) or requirement_id,
                "description": _trim_text(requirement.description, _MAX_TASK_QUESTION_LENGTH),
                "coverage_tags": [tag.casefold() for tag in requirement.coverage_tags if _as_text(tag)],
                "heading": _coverage_requirement_heading(
                    {
                        "requirement_id": requirement_id,
                        "title": requirement.title,
                    },
                    labels,
                ),
            }
        )
    return normalized


def _coverage_requirement_heading(
    requirement: dict[str, Any],
    labels: ReportLabels | None = None,
) -> str:
    explicit_heading = _trim_text(_as_text(requirement.get("heading")), _MAX_REPORT_HEADING_LENGTH)
    if explicit_heading:
        return explicit_heading
    title = _trim_text(_as_text(requirement.get("title")), _MAX_REPORT_HEADING_LENGTH)
    if title:
        return title
    return labels.risks_heading if labels else "Analysis"


def _coverage_requirement_purpose(requirement: dict[str, Any]) -> str:
    heading = _coverage_requirement_heading(requirement)
    description = _trim_text(_as_text(requirement.get("description")), _MAX_TASK_QUESTION_LENGTH)
    if description:
        return description
    return f"Explain the evidence-backed answer for {heading}."


def _findings_for_requirement(
    tasks: list[dict],
    requirement: dict[str, Any],
    findings: list[dict],
) -> list[dict]:
    matching_task_ids = {
        _as_text(task.get("task_id"))
        for task in tasks
        if _task_matches_requirement(task, requirement)
    }
    related_findings = [
        item for item in findings if _as_text(item.get("task_id")) in matching_task_ids
    ]
    filtered = _filter_findings_for_requirement(requirement, related_findings or findings)
    if filtered:
        return filtered
    return related_findings


def _task_matches_requirement(task: dict[str, Any], requirement: dict[str, Any]) -> bool:
    task_tags = {tag.casefold() for tag in _as_string_list(task.get("coverage_tags"))}
    requirement_tags = {tag.casefold() for tag in _as_string_list(requirement.get("coverage_tags"))}
    return bool(task_tags & requirement_tags)


def _filter_findings_for_requirement(
    requirement: dict[str, Any],
    findings: list[dict],
) -> list[dict]:
    tags = {tag.casefold() for tag in _as_string_list(requirement.get("coverage_tags"))}
    if not findings:
        return []
    if "risks" in tags or "tradeoffs" in tags:
        filtered = [
            item
            for item in findings
            if _as_text(item.get("evidence_type")) in {"risk", "limitation", "comparison"}
        ]
        return filtered or [item for item in findings if _is_risk_finding(item)]
    if "scope" in tags or "definitions" in tags:
        filtered = [
            item
            for item in findings
            if _as_text(item.get("evidence_type")) in {"definition", "fact"}
        ]
        return filtered or [item for item in findings if not _is_risk_finding(item)]
    if "recent" in tags or "examples" in tags or "evidence" in tags:
        filtered = [
            item
            for item in findings
            if _as_text(item.get("evidence_type")) in {"example", "comparison", "statistic", "trend", "fact"}
        ]
        return filtered or [item for item in findings if not _is_risk_finding(item)]
    return list(findings)


def _has_risk_requirement(coverage_requirements: list[dict[str, Any]]) -> bool:
    for requirement in coverage_requirements:
        tags = {tag.casefold() for tag in _as_string_list(requirement.get("coverage_tags"))}
        if "risks" in tags or "tradeoffs" in tags:
            return True
    return False


def _task_report_heading(task: dict[str, Any]) -> str:
    report_heading = _sanitize_report_heading(_as_text(task.get("report_heading")))
    if not report_heading:
        raise LLMOutputInvalidError(
            f"Task `{_as_text(task.get('task_id')) or 'unknown'}` is missing a valid report heading.",
        )
    return report_heading


def _task_section_purpose(task: dict[str, Any]) -> str:
    question = _trim_text(_as_text(task.get("question")), _MAX_TASK_QUESTION_LENGTH)
    heading = _task_report_heading(task)
    if question:
        return f"Explain the evidence-backed answer for {heading}. Focus on: {question}"
    return f"Explain the evidence-backed answer for {heading}."


def _generate_report_headings_with_llm(
    question: str,
    tasks: list[dict],
    findings: list[dict],
    settings: Settings,
    labels: ReportLabels,
) -> dict[str, str]:
    if not tasks:
        return {}

    try:
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError as exc:
        raise LLMInvocationError("Report heading generation dependencies are not installed.") from exc

    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You rewrite internal research tasks into concise report chapter headings. "
                "Keep the original scope and terminology. "
                "Use the user's language. "
                "Return topical headings, not commands and not questions. "
                "Do not include markdown, citations, numbering, or trailing punctuation. "
                "Make headings distinct from each other.",
            ),
            (
                "human",
                "Current question:\n{question}\n\n"
                "Report language:\n{language_name}\n\n"
                "Tasks:\n{tasks}\n\n"
                "Return one heading per task using the same task_id values.",
            ),
        ]
    )
    model = build_structured_chat_model(settings.synthesis_model, settings, TaskReportHeadingPlan, temperature=0)
    if model is None:
        raise LLMInvocationError("Report heading generation model could not be initialized.")

    chain = prompt | model
    try:
        response: TaskReportHeadingPlan = chain.invoke(
            {
                "question": question,
                "language_name": labels.language_name,
                "tasks": _build_heading_prompt_tasks(tasks, findings),
            }
        )
    except Exception as exc:
        raise LLMInvocationError("Report heading generation failed.") from exc

    return {
        item.task_id: item.report_heading
        for item in response.tasks
        if item.task_id.strip() and item.report_heading.strip()
    }


def _build_heading_prompt_tasks(tasks: list[dict], findings: list[dict]) -> list[dict[str, Any]]:
    evidence_by_task: dict[str, list[str]] = defaultdict(list)
    seen_claims: dict[str, set[str]] = defaultdict(set)
    for finding in _sort_findings_for_synthesis(findings):
        task_id = _as_text(finding.get("task_id"))
        claim = _trim_text(
            _as_text(finding.get("claim")) or _as_text(finding.get("snippet")),
            _MAX_CLAIM_LENGTH,
        )
        if not task_id or not claim or len(evidence_by_task[task_id]) >= 2:
            continue
        dedupe_key = claim.casefold()
        if dedupe_key in seen_claims[task_id]:
            continue
        seen_claims[task_id].add(dedupe_key)
        evidence_by_task[task_id].append(claim)

    prompt_tasks: list[dict[str, Any]] = []
    for task in tasks:
        task_id = _as_text(task.get("task_id"))
        if not task_id:
            continue
        prompt_tasks.append(
            {
                "task_id": task_id,
                "title": _trim_text(_as_text(task.get("title")), _MAX_TASK_TITLE_LENGTH) or task_id,
                "question": _trim_text(_as_text(task.get("question")), _MAX_TASK_QUESTION_LENGTH),
                "evidence": evidence_by_task.get(task_id, []),
            }
        )
    return prompt_tasks


def _finalize_task_report_headings(
    tasks: list[dict],
    drafted: dict[str, str],
    labels: ReportLabels,
) -> list[dict]:
    reserved = {
        labels.summary_heading.casefold(),
        labels.risks_heading.casefold(),
        labels.conclusion_heading.casefold(),
        labels.references_heading.casefold(),
    }
    seen: set[str] = set()
    finalized: list[dict] = []
    for task in tasks:
        task_id = _as_text(task.get("task_id"))
        chosen = _sanitize_report_heading(drafted.get(task_id, "") or _as_text(task.get("report_heading")))
        if not chosen:
            raise LLMOutputInvalidError(f"Report heading generation returned no heading for task `{task_id}`.")
        key = chosen.casefold()
        if key in reserved:
            raise LLMOutputInvalidError(f"Report heading `{chosen}` conflicts with a reserved report section.")
        if key in seen:
            raise LLMOutputInvalidError(f"Report heading `{chosen}` is duplicated across tasks.")

        updated_task = dict(task)
        updated_task["report_heading"] = chosen
        finalized.append(updated_task)
        seen.add(key)
    return finalized


def _sanitize_report_heading(value: str) -> str:
    normalized = _normalize_space(value.lstrip("#").strip())
    normalized = re.sub(r"\s*\[[^\]]+\]\s*$", "", normalized)
    normalized = normalized.rstrip(" .:;。；：")
    return _trim_text(normalized, _MAX_REPORT_HEADING_LENGTH)


def _select_diverse_findings(findings: list[dict], limit: int) -> list[dict]:
    selected: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for item in findings:
        key = (
            str(item.get("source_id", "")).strip(),
            str(item.get("evidence_type", "")).strip(),
            str(item.get("claim", "")).strip().casefold(),
        )
        if key in seen:
            continue
        seen.add(key)
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def _sort_findings_for_synthesis(findings: list[dict]) -> list[dict]:
    return sorted(findings, key=_finding_rank, reverse=True)


def _finding_rank(finding: dict[str, Any]) -> tuple[float, float]:
    return (
        _as_optional_float(finding.get("confidence")) or 0.0,
        _as_optional_float(finding.get("relevance_score")) or 0.0,
    )


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _as_optional_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for item in value if (text := _as_text(item))]


def _normalize_space(value: str) -> str:
    return " ".join(value.split()).strip()


def _trim_text(value: str, max_chars: int) -> str:
    normalized = _normalize_space(value)
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."
