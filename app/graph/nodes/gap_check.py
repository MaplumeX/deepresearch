from langchain_core.runnables import RunnableConfig

from app.domain.models import (
    CoverageRequirement,
    QualityGateResult,
    ResearchRequest,
    ResearchTask,
    ResearchTaskOutcome,
)
from app.runtime_progress import emit_progress
from app.services.research_quality import (
    build_retry_tasks,
    evaluate_quality_gate,
    format_quality_gate_warning,
    identify_research_gaps,
)
from app.services.research_progress import build_counts, build_progress_payload
from app.services.research_progress import (
    build_gap_progress,
    build_progress_action,
    build_retry_task_progress,
)


def gap_check(state: dict, config: RunnableConfig | None = None) -> dict:
    tasks = [ResearchTask.model_validate(item) for item in state.get("tasks", [])]
    task_outcomes = [
        ResearchTaskOutcome.model_validate(item)
        for item in state.get("task_outcomes", [])
    ]
    coverage_requirements = [
        CoverageRequirement.model_validate(item)
        for item in state.get("coverage_requirements", [])
    ]
    gaps = identify_research_gaps(
        tasks,
        task_outcomes,
        findings=list(state.get("findings", [])),
        sources=dict(state.get("sources", {})),
        coverage_requirements=coverage_requirements,
    )
    request = ResearchRequest.model_validate(state["request"])
    has_iteration_budget = state.get("iteration_count", 0) < request.max_iterations
    updated_tasks = (
        build_retry_tasks(tasks, task_outcomes, gaps)
        if has_iteration_budget
        else [task.model_copy(update={"status": "done"}) for task in tasks]
    )
    quality_gate = evaluate_quality_gate(
        gaps,
        has_iteration_budget=has_iteration_budget,
    )
    if any(task.status == "pending" for task in updated_tasks):
        quality_gate = quality_gate.model_copy(update={"should_replan": False})

    progress_action = None
    if any(task.status == "pending" for task in updated_tasks):
        progress_action = build_progress_action(
            "targeted_retry",
            label="优先局部重试",
            detail="当前缺口可以通过扩查询或扩抓取修复，先不进入整轮重规划。",
        )
    elif quality_gate.should_replan:
        progress_action = build_progress_action(
            "replan",
            label="进入下一轮规划",
            detail="局部重试不足以补齐当前缺口，准备生成新的研究任务。",
        )
    elif quality_gate.requires_review:
        progress_action = build_progress_action(
            "review",
            label="等待人工复核",
            detail="迭代预算已耗尽，系统停止继续搜索并等待人工决策。",
        )

    progress_gaps = build_gap_progress(gaps)
    progress_retry_tasks = build_retry_task_progress(updated_tasks, gaps)

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
                action=progress_action,
                gaps=progress_gaps,
                retry_tasks=progress_retry_tasks,
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
                action=progress_action,
                gaps=progress_gaps,
                ).model_dump(),
            },
        )

    return {
        "gaps": [gap.model_dump() for gap in gaps],
        "tasks": [task.model_dump() if isinstance(task, ResearchTask) else task for task in updated_tasks],
        "quality_gate": quality_gate.model_dump(),
        "warnings": warnings,
        "review_required": bool(state.get("review_required", False)) or quality_gate.requires_review,
    }


def after_gap_check(state: dict) -> str:
    if any(task.get("status") == "pending" for task in state.get("tasks", [])):
        return "dispatch_tasks"
    quality_gate = QualityGateResult.model_validate(state.get("quality_gate", {}))
    if quality_gate.should_replan:
        return "plan_research"
    return "synthesize_report"
