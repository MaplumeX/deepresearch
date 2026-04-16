from langchain_core.runnables import RunnableConfig

from app.runtime_progress import emit_progress
from app.services.research_progress import build_counts, build_progress_payload


def finalize(state: dict, config: RunnableConfig | None = None) -> dict:
    emit_progress(
        config,
        {
            "message": "Finalizing the research response.",
            "progress": build_progress_payload(
                "finalizing",
                iteration=state.get("iteration_count"),
                max_iterations=state.get("request", {}).get("max_iterations"),
                counts=build_counts(
                    planned_tasks=len(state.get("tasks", [])),
                    completed_tasks=len(state.get("task_outcomes", [])),
                    kept_sources=len(state.get("sources", {})),
                    evidence_count=len(state.get("findings", [])),
                    warnings=len(state.get("warnings", [])),
                ),
                review_required=bool(state.get("review_required", False)),
                review_kind="human_review" if state.get("review_required") else None,
            ).model_dump(),
        },
    )
    final_report = state.get("final_report") or state.get("draft_report", "")
    final_structured_report = state.get("final_structured_report") or state.get("draft_structured_report", {})
    return {
        "final_report": final_report,
        "final_structured_report": final_structured_report,
    }
