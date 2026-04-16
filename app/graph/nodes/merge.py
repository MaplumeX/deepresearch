from langchain_core.runnables import RunnableConfig

from app.runtime_progress import emit_progress
from app.services.dedupe import dedupe_findings
from app.services.research_progress import build_counts, build_progress_payload, count_completed_tasks


def merge_evidence(state: dict, config: RunnableConfig | None = None) -> dict:
    sources = dict(state.get("sources", {}))
    for batch in state.get("raw_source_batches", []):
        sources.update(batch)
    findings = dedupe_findings(list(state.get("raw_findings", [])))
    emit_progress(
        config,
        {
            "message": "Merging evidence across completed tasks.",
            "progress": build_progress_payload(
                "merging_evidence",
                iteration=state.get("iteration_count"),
                max_iterations=state.get("request", {}).get("max_iterations"),
                counts=build_counts(
                    planned_tasks=len(state.get("tasks", [])),
                    completed_tasks=count_completed_tasks(state.get("task_outcomes", [])),
                    kept_sources=len(sources),
                    evidence_count=len(findings),
                    warnings=len(state.get("warnings", [])),
                ),
            ).model_dump(),
        },
    )
    return {
        "findings": findings,
        "sources": sources,
    }
