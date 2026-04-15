from __future__ import annotations

from app.domain.models import QualityGateResult, ResearchRequest, ResearchTask, ResearchTaskOutcome
from app.runtime_progress import emit_progress
from app.services.research_quality import (
    evaluate_quality_gate,
    format_quality_gate_warning,
    identify_research_gaps,
)
from app.services.research_progress import build_counts, build_progress_payload


def gap_check(state: dict, config: dict | None = None) -> dict:
    tasks = [ResearchTask.model_validate(item) for item in state.get("tasks", [])]
    task_outcomes = [
        ResearchTaskOutcome.model_validate(item)
        for item in state.get("task_outcomes", [])
    ]
    gaps = identify_research_gaps(tasks, task_outcomes)
    request = ResearchRequest.model_validate(state["request"])
    has_iteration_budget = state.get("iteration_count", 0) < request.max_iterations
    quality_gate = evaluate_quality_gate(
        gaps,
        has_iteration_budget=has_iteration_budget,
    )

    warnings = list(state.get("warnings", []))
    if not quality_gate.passed and quality_gate.requires_review:
        warning = format_quality_gate_warning(quality_gate)
        if warning and warning not in warnings:
            warnings.append(warning)

    emit_progress(
        config,
        {
            "message": "Checking research quality and remaining gaps.",
            "progress": build_progress_payload(
                "checking_gaps",
                iteration=state.get("iteration_count"),
                max_iterations=request.max_iterations,
                counts=build_counts(
                    planned_tasks=len(tasks),
                    completed_tasks=len(task_outcomes),
                    kept_sources=len(state.get("sources", {})),
                    evidence_count=len(state.get("findings", [])),
                    warnings=len(warnings),
                ),
                review_required=quality_gate.requires_review,
                review_kind="human_review" if quality_gate.requires_review else None,
            ).model_dump(),
        },
    )
    if quality_gate.should_replan:
        emit_progress(
            config,
            {
                "message": "Research quality gate requested another planning iteration.",
                "progress": build_progress_payload(
                    "replanning",
                    iteration=state.get("iteration_count"),
                    max_iterations=request.max_iterations,
                    counts=build_counts(
                        planned_tasks=len(tasks),
                        completed_tasks=len(task_outcomes),
                        kept_sources=len(state.get("sources", {})),
                        evidence_count=len(state.get("findings", [])),
                        warnings=len(warnings),
                    ),
                ).model_dump(),
            },
        )

    return {
        "gaps": [gap.model_dump() for gap in gaps],
        "quality_gate": quality_gate.model_dump(),
        "warnings": warnings,
        "review_required": bool(state.get("review_required", False)) or quality_gate.requires_review,
    }


def after_gap_check(state: dict) -> str:
    quality_gate = QualityGateResult.model_validate(state.get("quality_gate", {}))
    if quality_gate.should_replan:
        return "plan_research"
    return "synthesize_report"
