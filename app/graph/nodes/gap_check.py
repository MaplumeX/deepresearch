from __future__ import annotations

from app.domain.models import QualityGateResult, ResearchRequest, ResearchTask, ResearchTaskOutcome
from app.services.research_quality import (
    evaluate_quality_gate,
    format_quality_gate_warning,
    identify_research_gaps,
)


def gap_check(state: dict) -> dict:
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
