from langchain_core.runnables import RunnableConfig

from app.config import get_settings
from app.runtime_progress import emit_progress
from app.services.research_progress import build_counts, build_progress_payload
from app.services.synthesis import assign_report_headings, synthesize_report


def synthesize_report_node(state: dict, config: RunnableConfig | None = None) -> dict:
    settings = get_settings()
    emit_progress(
        config,
        {
            "message": "Synthesizing the research report.",
            "progress": build_progress_payload(
                "synthesizing",
                iteration=state.get("iteration_count"),
                max_iterations=state.get("request", {}).get("max_iterations"),
                counts=build_counts(
                    planned_tasks=len(state.get("tasks", [])),
                    completed_tasks=len(state.get("task_outcomes", [])),
                    kept_sources=len(state.get("sources", {})),
                    evidence_count=len(state.get("findings", [])),
                    warnings=len(state.get("warnings", [])),
                ),
            ).model_dump(),
        },
    )
    tasks = assign_report_headings(
        question=state["request"]["question"],
        tasks=state.get("tasks", []),
        findings=state.get("findings", []),
        settings=settings,
        output_language=state.get("request", {}).get("output_language"),
    )
    report = synthesize_report(
        question=state["request"]["question"],
        tasks=tasks,
        findings=state.get("findings", []),
        sources=state.get("sources", {}),
        settings=settings,
        memory=state.get("memory"),
        output_language=state.get("request", {}).get("output_language"),
    )
    return {
        "tasks": tasks,
        "draft_report": report.markdown,
        "draft_structured_report": report.model_dump(),
    }
