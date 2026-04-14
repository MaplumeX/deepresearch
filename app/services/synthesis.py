from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.config import Settings
from app.domain.models import ReportDraft, ReportSectionDraft, StructuredReport
from app.services.conversation_memory import format_memory_for_prompt
from app.services.llm import build_chat_model, can_use_llm
from app.services.report_contract import build_structured_report


def _fallback_report(
    question: str,
    tasks: list[dict],
    findings: list[dict],
) -> ReportDraft:
    grouped: dict[str, list[dict]] = defaultdict(list)
    titles = {task["task_id"]: task["title"] for task in tasks}
    for finding in findings:
        grouped[finding["task_id"]].append(finding)

    summary_claims = findings[:3]
    summary_lines = [
        f"- {item['claim']} [{item['source_id']}]"
        for item in summary_claims
    ] or ["- No evidence was collected yet."]

    analysis_sections: list[ReportSectionDraft] = []
    for task in tasks:
        task_findings = grouped.get(task["task_id"], [])
        lines = [
            f"- {item['claim']} [{item['source_id']}]"
            for item in task_findings
        ] or ["- No evidence collected for this task."]
        analysis_sections.append(
            ReportSectionDraft(
                heading=titles[task["task_id"]],
                body_markdown="\n".join(lines),
            )
        )

    if not tasks:
        analysis_sections.append(
            ReportSectionDraft(
                heading="Analysis",
                body_markdown=f"Question: {question}",
            )
        )

    return ReportDraft(
        title="Research Report",
        summary="\n".join(summary_lines),
        sections=analysis_sections,
    )


def _maybe_synthesize_with_llm(
    question: str,
    tasks: list[dict],
    findings: list[dict],
    sources: dict[str, dict],
    settings: Settings,
    memory: dict[str, Any] | None,
) -> ReportDraft | None:
    if not settings.enable_llm_synthesis or not can_use_llm(settings) or not findings:
        return None

    try:
        from langchain_core.output_parsers import PydanticOutputParser
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError:
        return None

    parser = PydanticOutputParser(pydantic_object=ReportDraft)
    memory_sections = format_memory_for_prompt(memory)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You synthesize structured cited reports from validated evidence. "
                "Conversation memory is background context only. "
                "Never use conversation memory as a citation source. "
                "Keep all factual citations in the form [source_id]. "
                "Return analysis sections only. Do not include a sources appendix.",
            ),
            (
                "human",
                "Current question:\n{question}\n\n"
                "Rolling summary:\n{rolling_summary}\n\n"
                "Recent 5 turns:\n{recent_turns}\n\n"
                "Known facts from older turns:\n{key_facts}\n\n"
                "Open questions from older turns:\n{open_questions}\n\n"
                "Current tasks:\n{tasks}\n\nFindings:\n{findings}\n\nSources:\n{sources}\n\n"
                "Write concise but well-structured analysis sections in markdown. "
                "Use inline citations on factual claims. "
                "{format_instructions}",
            ),
        ]
    )
    model = build_chat_model(settings.synthesis_model, settings, temperature=0)
    if model is None:
        return None

    chain = prompt | model | parser
    return chain.invoke(
        {
            "question": question,
            "rolling_summary": memory_sections["rolling_summary"],
            "recent_turns": memory_sections["recent_turns"],
            "key_facts": memory_sections["key_facts"],
            "open_questions": memory_sections["open_questions"],
            "tasks": tasks,
            "findings": findings,
            "sources": sources,
            "format_instructions": parser.get_format_instructions(),
        }
    )


def synthesize_report(
    question: str,
    tasks: list[dict],
    findings: list[dict],
    sources: dict[str, dict],
    settings: Settings,
    memory: dict[str, Any] | None = None,
) -> StructuredReport:
    drafted = _maybe_synthesize_with_llm(question, tasks, findings, sources, settings, memory)
    if drafted is None:
        drafted = _fallback_report(question, tasks, findings)
    drafted = _ensure_memory_section(drafted, memory)
    return build_structured_report(drafted, sources=sources, findings=findings)


def _build_memory_section(memory: dict[str, Any] | None) -> str:
    memory_sections = format_memory_for_prompt(memory)
    if all(value == "None" for value in memory_sections.values()):
        return ""
    return "\n".join(
        [
            "_Background only. Not a citation source._",
            f"Earlier context:\n{memory_sections['rolling_summary']}",
            f"Recent 5 turns:\n{memory_sections['recent_turns']}",
            f"Older key facts:\n{memory_sections['key_facts']}",
            f"Open questions:\n{memory_sections['open_questions']}",
        ]
    )


def _ensure_memory_section(draft: ReportDraft, memory: dict[str, Any] | None) -> ReportDraft:
    memory_section = _build_memory_section(memory)
    if not memory_section:
        return draft
    if any(section.heading == "Conversation Context" for section in draft.sections):
        return draft
    return ReportDraft(
        title=draft.title,
        summary=draft.summary,
        sections=[
            ReportSectionDraft(
                heading="Conversation Context",
                body_markdown=memory_section,
            ),
            *draft.sections,
        ],
    )
