from __future__ import annotations

from collections.abc import Sequence

from app.domain.models import (
    ResearchProgressCounts,
    ResearchProgressPayload,
    ResearchProgressPhase,
    ResearchReviewProgress,
    ResearchTask,
    ResearchTaskOutcome,
    ResearchTaskProgress,
    ResearchWorkerStep,
)


PHASE_LABELS: dict[ResearchProgressPhase, str] = {
    "queued": "Queued",
    "clarifying_scope": "Clarifying scope",
    "planning": "Planning research",
    "executing_tasks": "Executing tasks",
    "merging_evidence": "Merging evidence",
    "checking_gaps": "Checking quality gaps",
    "replanning": "Replanning",
    "synthesizing": "Synthesizing report",
    "auditing": "Auditing citations",
    "awaiting_review": "Awaiting review",
    "finalizing": "Finalizing",
    "completed": "Completed",
    "failed": "Failed",
}


def build_counts(
    *,
    planned_tasks: int | None = None,
    completed_tasks: int | None = None,
    search_hits: int | None = None,
    acquired_contents: int | None = None,
    kept_sources: int | None = None,
    evidence_count: int | None = None,
    warnings: int | None = None,
) -> ResearchProgressCounts:
    return ResearchProgressCounts(
        planned_tasks=planned_tasks,
        completed_tasks=completed_tasks,
        search_hits=search_hits,
        acquired_contents=acquired_contents,
        kept_sources=kept_sources,
        evidence_count=evidence_count,
        warnings=warnings,
    )


def build_task_progress(
    task: ResearchTask | dict | None,
    *,
    index: int | None = None,
    total: int | None = None,
    status: str = "running",
    worker_step: ResearchWorkerStep | None = None,
) -> ResearchTaskProgress | None:
    if task is None:
        return None
    parsed = task if isinstance(task, ResearchTask) else ResearchTask.model_validate(task)
    if index is None or total is None:
        return None
    return ResearchTaskProgress(
        task_id=parsed.task_id,
        title=parsed.title,
        index=index,
        total=total,
        status=status,
        worker_step=worker_step,
    )


def count_completed_tasks(task_outcomes: Sequence[ResearchTaskOutcome | dict]) -> int:
    return len(task_outcomes)


def build_progress_payload(
    phase: ResearchProgressPhase,
    *,
    iteration: int | None = None,
    max_iterations: int | None = None,
    task: ResearchTaskProgress | None = None,
    counts: ResearchProgressCounts | None = None,
    review_required: bool = False,
    review_kind: str | None = None,
    phase_label: str | None = None,
) -> ResearchProgressPayload:
    return ResearchProgressPayload(
        phase=phase,
        phase_label=phase_label or PHASE_LABELS[phase],
        iteration=iteration,
        max_iterations=max_iterations,
        task=task,
        counts=counts or ResearchProgressCounts(),
        review=ResearchReviewProgress(required=review_required, kind=review_kind),
    )
