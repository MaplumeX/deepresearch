from __future__ import annotations

from collections import defaultdict

from app.config import Settings
from app.domain.models import ReportDraft
from app.services.llm import build_chat_model, can_use_llm


def _fallback_markdown(question: str, tasks: list[dict], findings: list[dict], sources: dict[str, dict]) -> ReportDraft:
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

    markdown = "\n\n".join(
        [
            f"# Research Report\n\nQuestion: {question}",
            "## Executive Summary\n" + "\n".join(summary_lines),
            *body_sections,
            "## Sources\n" + "\n".join(source_lines),
        ]
    )
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
) -> ReportDraft | None:
    if not settings.enable_llm_synthesis or not can_use_llm(settings) or not findings:
        return None

    try:
        from langchain_core.output_parsers import PydanticOutputParser
        from langchain_core.prompts import ChatPromptTemplate
    except ImportError:
        return None

    parser = PydanticOutputParser(pydantic_object=ReportDraft)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "You synthesize cited markdown reports from validated evidence. "
                "Keep all citations in the form [source_id].",
            ),
            (
                "human",
                "Question:\n{question}\n\nTasks:\n{tasks}\n\nFindings:\n{findings}\n\nSources:\n{sources}\n\n"
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
) -> ReportDraft:
    drafted = _maybe_synthesize_with_llm(question, tasks, findings, sources, settings)
    if drafted:
        return drafted
    return _fallback_markdown(question, tasks, findings, sources)
