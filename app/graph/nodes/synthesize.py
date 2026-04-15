from __future__ import annotations

from app.config import get_settings
from app.runtime_progress import emit_progress
from app.services.research_progress import build_counts, build_progress_payload
from app.services.synthesis import synthesize_report


def synthesize_report_node(state: dict, config: dict | None = None) -> dict:
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
    report = synthesize_report(
        question=state["request"]["question"],
        tasks=state.get("tasks", []),
        findings=state.get("findings", []),
        sources=state.get("sources", {}),
        settings=get_settings(),
        memory=state.get("memory"),
    )
    return {
        "draft_report": report.markdown,
        "draft_structured_report": report.model_dump(),
    }
