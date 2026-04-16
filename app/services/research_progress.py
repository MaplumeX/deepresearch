from __future__ import annotations

from collections.abc import Sequence

from app.domain.models import (
    ResearchGap,
    ResearchProgressAction,
    ResearchProgressCounts,
    ResearchProgressGap,
    ResearchProgressPayload,
    ResearchProgressPhase,
    ResearchReviewProgress,
    ResearchRetryTaskProgress,
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
    completed_task_ids: set[str] = set()
    for item in task_outcomes:
        task_id = item.task_id if isinstance(item, ResearchTaskOutcome) else str(item.get("task_id", "")).strip()
        if task_id:
            completed_task_ids.add(task_id)
    return len(completed_task_ids)


def build_progress_payload(
    phase: ResearchProgressPhase,
    *,
    iteration: int | None = None,
    max_iterations: int | None = None,
    task: ResearchTaskProgress | None = None,
    counts: ResearchProgressCounts | None = None,
    action: ResearchProgressAction | None = None,
    gaps: Sequence[ResearchProgressGap] | None = None,
    retry_tasks: Sequence[ResearchRetryTaskProgress] | None = None,
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
        action=action,
        gaps=list(gaps or []),
        retry_tasks=list(retry_tasks or []),
        review=ResearchReviewProgress(required=review_required, kind=review_kind),
    )


def build_progress_action(
    kind: str,
    *,
    label: str,
    detail: str | None = None,
) -> ResearchProgressAction:
    return ResearchProgressAction(kind=kind, label=label, detail=detail)


def build_gap_progress(
    gaps: Sequence[ResearchGap | dict],
    *,
    limit: int = 3,
) -> list[ResearchProgressGap]:
    normalized: list[ResearchGap] = []
    for item in gaps:
        try:
            normalized.append(item if isinstance(item, ResearchGap) else ResearchGap.model_validate(item))
        except Exception:
            continue
    normalized.sort(key=lambda gap: (_severity_rank(gap.severity), gap.title.casefold(), gap.task_id))
    return [
        ResearchProgressGap(
            task_id=gap.task_id,
            title=gap.title,
            gap_type=gap.gap_type,
            severity=gap.severity,
            retry_action=gap.retry_action,
            scope="global" if gap.task_id.startswith("coverage-") else "task",
        )
        for gap in normalized[:limit]
    ]


def build_retry_task_progress(
    tasks: Sequence[ResearchTask | dict],
    gaps: Sequence[ResearchGap | dict],
    *,
    limit: int = 3,
) -> list[ResearchRetryTaskProgress]:
    action_by_task = _retry_action_by_task(gaps)
    progress_items: list[ResearchRetryTaskProgress] = []
    for item in tasks:
        try:
            task = item if isinstance(item, ResearchTask) else ResearchTask.model_validate(item)
        except Exception:
            continue
        if task.status != "pending":
            continue
        progress_items.append(
            ResearchRetryTaskProgress(
                task_id=task.task_id,
                title=task.title,
                retry_action=action_by_task.get(task.task_id),
                retry_count=task.retry_count,
                query_budget=task.query_budget,
                fetch_budget=task.fetch_budget,
            )
        )
        if len(progress_items) >= limit:
            break
    return progress_items


def _retry_action_by_task(gaps: Sequence[ResearchGap | dict]) -> dict[str, str]:
    action_by_task: dict[str, str] = {}
    priority = {"expand_fetch": 0, "expand_queries": 1, "replan": 2}
    for item in gaps:
        try:
            gap = item if isinstance(item, ResearchGap) else ResearchGap.model_validate(item)
        except Exception:
            continue
        if gap.retry_action is None:
            continue
        current = action_by_task.get(gap.task_id)
        if current is None or priority[gap.retry_action] < priority[current]:
            action_by_task[gap.task_id] = gap.retry_action
    return action_by_task


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 99)
