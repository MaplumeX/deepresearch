from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.config import Settings
from app.domain.models import ReportDraft
from app.services.conversation_memory import format_memory_for_prompt
from app.services.llm import build_chat_model, can_use_llm


def _fallback_markdown(
    question: str,
    tasks: list[dict],
    findings: list[dict],
    sources: dict[str, dict],
    memory: dict[str, Any] | None,
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

    body_sections: list[str] = []
    for task in tasks:
        task_findings = grouped.get(task["task_id"], [])
        lines = [
            f"- {item['claim']} [{item['source_id']}]"
            for item in task_findings
        ] or ["- No evidence collected for this task."]
        section = "\n".join([f"## {titles[task['task_id']]}", *lines])
        body_sections.append(section)

    source_lines = [
        f"- [{source_id}] {source['title']} - {source['url']}"
        for source_id, source in sorted(sources.items())
    ] or ["- No sources available."]

    sections = [f"# Research Report\n\nQuestion: {question}"]
    memory_section = _build_memory_section(memory)
    if memory_section:
        sections.append(memory_section)
    sections.extend(
        [
            "## Executive Summary\n" + "\n".join(summary_lines),
            *body_sections,
            "## Sources\n" + "\n".join(source_lines),
        ]
    )
    markdown = "\n\n".join(sections)
    return ReportDraft(
        title="Research Report",
        summary="\n".join(summary_lines),
        markdown=markdown,
        cited_source_ids=sorted({item["source_id"] for item in findings}),
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
                "You synthesize cited markdown reports from validated evidence. "
                "Conversation memory is background context only. "
                "Never use conversation memory as a citation source. "
                "Keep all citations in the form [source_id].",
            ),
            (
                "human",
                "Current question:\n{question}\n\n"
                "Rolling summary:\n{rolling_summary}\n\n"
                "Recent 5 turns:\n{recent_turns}\n\n"
                "Known facts from older turns:\n{key_facts}\n\n"
                "Open questions from older turns:\n{open_questions}\n\n"
                "Current tasks:\n{tasks}\n\nFindings:\n{findings}\n\nSources:\n{sources}\n\n"
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
) -> ReportDraft:
    drafted = _maybe_synthesize_with_llm(question, tasks, findings, sources, settings, memory)
    if drafted:
        return drafted
    return _fallback_markdown(question, tasks, findings, sources, memory)


def _build_memory_section(memory: dict[str, Any] | None) -> str:
    memory_sections = format_memory_for_prompt(memory)
    if all(value == "None" for value in memory_sections.values()):
        return ""
    return "\n".join(
        [
            "## Conversation Context",
            "_Background only. Not a citation source._",
            f"Earlier context:\n{memory_sections['rolling_summary']}",
            f"Recent 5 turns:\n{memory_sections['recent_turns']}",
            f"Older key facts:\n{memory_sections['key_facts']}",
            f"Open questions:\n{memory_sections['open_questions']}",
        ]
    )
