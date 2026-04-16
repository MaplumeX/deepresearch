from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

from app.domain.models import (
    CoverageRequirement,
    QualityGateResult,
    ResearchGap,
    ResearchTask,
    ResearchTaskOutcome,
)

_MAX_QUERY_BUDGET = 6
_MAX_FETCH_BUDGET = 10
_MAX_TARGETED_RETRIES = 2


def build_task_outcome(
    task: ResearchTask,
    *,
    query_count: int,
    total_query_count: int = 0,
    search_hit_count: int,
    acquired_content_count: int,
    kept_source_count: int,
    evidence_count: int,
    source_urls: list[str],
    executed_queries: list[str] | None = None,
    used_urls: list[str] | None = None,
    stage_status: dict[str, str] | None = None,
) -> ResearchTaskOutcome:
    host_count = len({_hostname(url) for url in source_urls if _hostname(url)})
    failure_reasons: list[str] = []

    if search_hit_count == 0:
        failure_reasons.append("no_search_hits")
    elif acquired_content_count == 0:
        failure_reasons.append("content_acquisition_failed")
    elif kept_source_count == 0:
        failure_reasons.append("insufficient_content")
    elif evidence_count == 0:
        failure_reasons.append("no_evidence_extracted")

    quality_status = _classify_quality_status(
        evidence_count=evidence_count,
        host_count=host_count,
    )

    return ResearchTaskOutcome(
        task_id=task.task_id,
        title=task.title,
        quality_status=quality_status,
        query_count=query_count,
        total_query_count=max(total_query_count, query_count),
        search_hit_count=search_hit_count,
        acquired_content_count=acquired_content_count,
        kept_source_count=kept_source_count,
        evidence_count=evidence_count,
        host_count=host_count,
        failure_reasons=failure_reasons,
        executed_queries=list(executed_queries or []),
        used_urls=list(used_urls or []),
        stage_status=dict(stage_status or {}),
    )


def normalize_gaps(raw_gaps: list[object]) -> list[ResearchGap]:
    normalized: list[ResearchGap] = []
    for index, raw_gap in enumerate(raw_gaps, start=1):
        if isinstance(raw_gap, str):
            text = " ".join(raw_gap.split()).strip()
            if not text:
                continue
            normalized.append(
                ResearchGap(
                    gap_type="weak_evidence",
                    task_id=f"legacy-gap-{index}",
                    title=text,
                    reason=text,
                    retry_hint=text,
                    severity="medium",
                )
            )
            continue
        try:
            normalized.append(ResearchGap.model_validate(raw_gap))
        except Exception:
            text = " ".join(str(raw_gap).split()).strip()
            if not text:
                continue
            normalized.append(
                ResearchGap(
                    gap_type="weak_evidence",
                    task_id=f"legacy-gap-{index}",
                    title=text,
                    reason=text,
                    retry_hint=text,
                    severity="medium",
                )
            )
    return normalized


def identify_research_gaps(
    tasks: list[ResearchTask],
    task_outcomes: list[ResearchTaskOutcome],
    findings: list[dict] | None = None,
    sources: dict[str, dict] | None = None,
    coverage_requirements: list[CoverageRequirement] | list[dict] | None = None,
) -> list[ResearchGap]:
    findings = findings or []
    sources = sources or {}
    normalized_requirements = _normalize_coverage_requirements(coverage_requirements)
    outcome_by_task = {outcome.task_id: outcome for outcome in task_outcomes}
    findings_by_task = _findings_by_task(findings)
    gaps: list[ResearchGap] = []

    for task in tasks:
        outcome = outcome_by_task.get(task.task_id)
        if outcome is None:
            gaps.append(
                ResearchGap(
                    gap_type="retrieval_failure",
                    task_id=task.task_id,
                    title=f"Recover worker execution for {task.title}",
                    reason="The task did not produce a worker outcome.",
                    retry_hint=f"Re-run the task for {task.title} and verify the worker completes all stages.",
                    severity="high",
                    retry_action="replan",
                )
            )
            continue

        failed_gap = _failed_gap(task, outcome)
        if failed_gap is not None:
            gaps.append(failed_gap)
            continue

        if outcome.host_count < 2:
            gaps.append(
                ResearchGap(
                    gap_type="low_source_diversity",
                    task_id=task.task_id,
                    title=f"Add independent corroboration for {task.title}",
                    reason="Evidence for this task comes from fewer than 2 independent hosts.",
                    retry_hint=f"Look for an additional independent source that can corroborate {task.title}.",
                    severity="medium",
                    retry_action=_evidence_retry_action(outcome),
                )
            )
            continue

        if outcome.evidence_count < 2:
            gaps.append(
                ResearchGap(
                    gap_type="weak_evidence",
                    task_id=task.task_id,
                    title=f"Strengthen evidence for {task.title}",
                    reason=f"Only {outcome.evidence_count} evidence item was retained for this task.",
                    retry_hint=f"Find another concrete fact, measurement, or explicit claim about {task.title}.",
                    severity="medium",
                    retry_action=_evidence_retry_action(outcome),
                )
            )

        gaps.extend(
            _build_coverage_gaps_for_task(
                task,
                task_findings=findings_by_task.get(task.task_id, []),
                sources=sources,
            )
        )

    if normalized_requirements:
        gaps.extend(
            identify_coverage_gaps(
                normalized_requirements,
                tasks=tasks,
                task_outcomes=task_outcomes,
                findings=findings,
                sources=sources,
            )
        )

    return gaps


def evaluate_quality_gate(
    gaps: list[ResearchGap],
    *,
    has_iteration_budget: bool,
) -> QualityGateResult:
    if not gaps:
        return QualityGateResult()

    reasons = [f"{gap.title}: {gap.reason}" for gap in gaps]
    return QualityGateResult(
        passed=False,
        should_replan=has_iteration_budget,
        requires_review=not has_iteration_budget,
        reasons=reasons,
    )


def format_gaps_for_prompt(gaps: list[ResearchGap]) -> str:
    if not gaps:
        return "None"
    return "\n".join(
        [
            f"- [{gap.severity}] {gap.gap_type}: {gap.title}\n  Reason: {gap.reason}\n  Retry hint: {gap.retry_hint}"
            for gap in sort_gaps(gaps)
        ]
    )


def format_quality_gate_warning(gate: QualityGateResult) -> str:
    if gate.passed or not gate.reasons:
        return ""
    summary = "; ".join(gate.reasons[:3])
    return f"Research quality gate did not pass before synthesis: {summary}"


def sort_gaps(gaps: list[ResearchGap]) -> list[ResearchGap]:
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    return sorted(
        gaps,
        key=lambda gap: (
            severity_rank.get(gap.severity, 99),
            gap.task_id,
            gap.title.casefold(),
        ),
    )


def build_retry_tasks(
    tasks: list[ResearchTask],
    task_outcomes: list[ResearchTaskOutcome],
    gaps: list[ResearchGap],
) -> list[ResearchTask]:
    if not tasks:
        return []

    outcome_by_task = {outcome.task_id: outcome for outcome in task_outcomes}
    action_by_task = _retry_action_by_task(gaps)
    updated_tasks: list[ResearchTask] = []

    for task in tasks:
        action = action_by_task.get(task.task_id)
        outcome = outcome_by_task.get(task.task_id)
        if action is None or task.retry_count >= _MAX_TARGETED_RETRIES:
            updated_tasks.append(task.model_copy(update={"status": "done"}))
            continue

        next_task = _retry_task(task, outcome, action)
        if next_task is None:
            updated_tasks.append(task.model_copy(update={"status": "failed"}))
            continue
        updated_tasks.append(next_task)

    return updated_tasks


def identify_coverage_gaps(
    coverage_requirements: list[CoverageRequirement],
    *,
    tasks: list[ResearchTask],
    task_outcomes: list[ResearchTaskOutcome],
    findings: list[dict],
    sources: dict[str, dict],
) -> list[ResearchGap]:
    if not coverage_requirements:
        return []

    outcome_by_task = {outcome.task_id: outcome for outcome in task_outcomes}
    findings_by_task = _findings_by_task(findings)
    gaps: list[ResearchGap] = []

    for requirement in coverage_requirements:
        related_tasks = [
            task
            for task in tasks
            if _task_matches_coverage_requirement(task, requirement)
        ]
        if not related_tasks:
            gaps.append(
                ResearchGap(
                    gap_type="coverage_gap",
                    task_id=f"coverage-{requirement.requirement_id}",
                    title=f"Cover {requirement.title}",
                    reason=f"The current plan does not include work for '{requirement.title}'.",
                    retry_hint=requirement.description,
                    severity="medium",
                    retry_action="replan",
                )
            )
            continue

        related_findings = [
            finding
            for task in related_tasks
            for finding in findings_by_task.get(task.task_id, [])
        ]
        related_sources = _task_sources(related_findings, sources)
        related_outcomes = [
            outcome_by_task.get(task.task_id)
            for task in related_tasks
            if outcome_by_task.get(task.task_id) is not None
        ]
        gap = _coverage_gap_for_requirement(
            requirement,
            related_tasks=related_tasks,
            related_outcomes=related_outcomes,
            related_findings=related_findings,
            related_sources=related_sources,
        )
        if gap is not None:
            gaps.append(gap)

    return gaps


def _normalize_coverage_requirements(
    coverage_requirements: list[CoverageRequirement] | list[dict] | None,
) -> list[CoverageRequirement]:
    normalized: list[CoverageRequirement] = []
    for item in coverage_requirements or []:
        try:
            normalized.append(CoverageRequirement.model_validate(item))
        except Exception:
            continue
    return normalized


def _classify_quality_status(*, evidence_count: int, host_count: int) -> str:
    if evidence_count == 0:
        return "failed"
    if evidence_count < 2 or host_count < 2:
        return "weak"
    return "ok"


def _failed_gap(task: ResearchTask, outcome: ResearchTaskOutcome) -> ResearchGap | None:
    if outcome.quality_status != "failed":
        return None

    if "no_search_hits" in outcome.failure_reasons:
        return ResearchGap(
            gap_type="retrieval_failure",
            task_id=task.task_id,
            title=f"Recover search coverage for {task.title}",
            reason="No ranked search results were available for this task.",
            retry_hint=f"Broaden the search framing and look for official, primary, or recent sources about {task.title}.",
            severity="high",
            retry_action="expand_queries" if _can_expand_queries(outcome) else "replan",
        )

    if "content_acquisition_failed" in outcome.failure_reasons:
        return ResearchGap(
            gap_type="retrieval_failure",
            task_id=task.task_id,
            title=f"Recover source acquisition for {task.title}",
            reason="Search hits were found, but no usable content could be acquired.",
            retry_hint=f"Look for alternative URLs or source types that can provide readable content for {task.title}.",
            severity="high",
            retry_action=_acquisition_retry_action(outcome),
        )

    if "insufficient_content" in outcome.failure_reasons:
        return ResearchGap(
            gap_type="missing_evidence",
            task_id=task.task_id,
            title=f"Recover substantive content for {task.title}",
            reason="Acquired pages were too thin or too noisy to keep as usable sources.",
            retry_hint=f"Prioritize pages with substantive text, data, or direct claims about {task.title}.",
            severity="high",
            retry_action=_acquisition_retry_action(outcome),
        )

    return ResearchGap(
        gap_type="missing_evidence",
        task_id=task.task_id,
        title=f"Recover extractable evidence for {task.title}",
        reason="Usable sources were kept, but no evidence claim was extracted.",
        retry_hint=f"Find sources that state concrete facts, numbers, or explicit conclusions about {task.title}.",
        severity="high",
        retry_action=_evidence_retry_action(outcome),
    )


def _hostname(url: str) -> str:
    return urlparse(url).hostname or ""


def _findings_by_task(findings: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for finding in findings:
        task_id = str(finding.get("task_id", "")).strip()
        if not task_id:
            continue
        grouped.setdefault(task_id, []).append(finding)
    return grouped


def _build_coverage_gaps_for_task(
    task: ResearchTask,
    *,
    task_findings: list[dict],
    sources: dict[str, dict],
) -> list[ResearchGap]:
    if not task_findings:
        return []

    task_sources = _task_sources(task_findings, sources)
    gaps: list[ResearchGap] = []

    if not any(_source_is_recent(source) for source in task_sources):
        gaps.append(
            ResearchGap(
                gap_type="coverage_gap",
                task_id=task.task_id,
                title=f"Add recent evidence for {task.title}",
                reason="Current evidence does not clearly include recent source material.",
                retry_hint=f"Look for recent sources, updates, or 2025-2026 material about {task.title}.",
                severity="medium",
                retry_action="replan",
            )
        )

    if not _has_evidence_type(task_findings, {"example", "comparison", "statistic"}):
        gaps.append(
            ResearchGap(
                gap_type="coverage_gap",
                task_id=task.task_id,
                title=f"Add examples or concrete data for {task.title}",
                reason="Current evidence lacks concrete examples, comparisons, or measurable data points.",
                retry_hint=f"Find a concrete case study, benchmark, or quantitative evidence for {task.title}.",
                severity="medium",
                retry_action="replan",
            )
        )

    if not _has_evidence_type(task_findings, {"risk", "limitation"}):
        gaps.append(
            ResearchGap(
                gap_type="coverage_gap",
                task_id=task.task_id,
                title=f"Add risks or limitations for {task.title}",
                reason="Current evidence does not cover risks, failure modes, or limitations.",
                retry_hint=f"Find sources that discuss risks, tradeoffs, or limitations of {task.title}.",
                severity="medium",
                retry_action="replan",
            )
        )

    return gaps


def _task_sources(task_findings: list[dict], sources: dict[str, dict]) -> list[dict]:
    resolved: list[dict] = []
    seen: set[str] = set()
    for finding in task_findings:
        source_id = str(finding.get("source_id", "")).strip()
        if not source_id or source_id in seen:
            continue
        source = sources.get(source_id)
        if not isinstance(source, dict):
            continue
        seen.add(source_id)
        resolved.append(source)
    return resolved


def _has_evidence_type(task_findings: list[dict], expected: set[str]) -> bool:
    for finding in task_findings:
        evidence_type = str(finding.get("evidence_type", "")).strip().casefold()
        if evidence_type in expected:
            return True
    return False


def _source_is_recent(source: dict) -> bool:
    metadata = source.get("metadata")
    if not isinstance(metadata, dict):
        return False

    provider_metadata = metadata.get("provider_metadata")
    if not isinstance(provider_metadata, dict):
        return False

    current_year = datetime.now(UTC).year
    for item in provider_metadata.values():
        if not isinstance(item, dict):
            continue

        published_date = str(item.get("published_date", "")).strip()
        if published_date:
            year = _extract_year(published_date)
            if year >= current_year - 1:
                return True

        age = str(item.get("age", "")).strip().casefold()
        if any(token in age for token in ("day", "week", "month", "天", "周", "月")):
            return True
        if age.startswith(("1 year", "a year", "1年", "一年")):
            return True
    return False


def _extract_year(raw_value: str) -> int:
    try:
        return datetime.fromisoformat(raw_value.replace("Z", "+00:00")).year
    except ValueError:
        if len(raw_value) >= 4 and raw_value[:4].isdigit():
            return int(raw_value[:4])
    return 0


def _task_matches_coverage_requirement(task: ResearchTask, requirement: CoverageRequirement) -> bool:
    task_tags = {tag.casefold() for tag in task.coverage_tags}
    requirement_tags = {tag.casefold() for tag in requirement.coverage_tags}
    return bool(task_tags & requirement_tags)


def _coverage_gap_for_requirement(
    requirement: CoverageRequirement,
    *,
    related_tasks: list[ResearchTask],
    related_outcomes: list[ResearchTaskOutcome],
    related_findings: list[dict],
    related_sources: list[dict],
) -> ResearchGap | None:
    if not related_findings and not any(outcome.evidence_count > 0 for outcome in related_outcomes):
        return ResearchGap(
            gap_type="coverage_gap",
            task_id=f"coverage-{requirement.requirement_id}",
            title=f"Cover {requirement.title}",
            reason=f"The current evidence does not yet cover '{requirement.title}'.",
            retry_hint=requirement.description,
            severity="medium",
            retry_action="replan",
        )

    tags = {tag.casefold() for tag in requirement.coverage_tags}
    if "recent" in tags and related_sources and not any(_source_is_recent(source) for source in related_sources):
        return ResearchGap(
            gap_type="coverage_gap",
            task_id=f"coverage-{requirement.requirement_id}",
            title=f"Add recent support for {requirement.title}",
            reason=f"Current evidence for '{requirement.title}' is not clearly recent.",
            retry_hint=requirement.description,
            severity="medium",
            retry_action="replan",
        )

    if "examples" in tags and not _has_evidence_type(related_findings, {"example", "comparison", "statistic"}):
        return ResearchGap(
            gap_type="coverage_gap",
            task_id=f"coverage-{requirement.requirement_id}",
            title=f"Add concrete support for {requirement.title}",
            reason=f"Current evidence for '{requirement.title}' lacks examples, comparisons, or measurable data.",
            retry_hint=requirement.description,
            severity="medium",
            retry_action="replan",
        )

    if ("risks" in tags or "tradeoffs" in tags) and not _has_evidence_type(
        related_findings,
        {"risk", "limitation", "comparison"},
    ):
        return ResearchGap(
            gap_type="coverage_gap",
            task_id=f"coverage-{requirement.requirement_id}",
            title=f"Add tradeoffs for {requirement.title}",
            reason=f"Current evidence for '{requirement.title}' does not cover risks, limitations, or tradeoffs.",
            retry_hint=requirement.description,
            severity="medium",
            retry_action="replan",
        )

    return None


def _retry_action_by_task(gaps: list[ResearchGap]) -> dict[str, str]:
    action_by_task: dict[str, str] = {}
    priority = {"expand_fetch": 0, "expand_queries": 1, "replan": 2}
    for gap in sort_gaps(gaps):
        if gap.retry_action is None:
            continue
        current = action_by_task.get(gap.task_id)
        if current is None or priority[gap.retry_action] < priority[current]:
            action_by_task[gap.task_id] = gap.retry_action
    return action_by_task


def _retry_task(
    task: ResearchTask,
    outcome: ResearchTaskOutcome | None,
    action: str,
) -> ResearchTask | None:
    if action == "expand_queries":
        next_budget = min(_MAX_QUERY_BUDGET, task.query_budget + 2)
        if next_budget <= task.query_budget:
            return None
        return task.model_copy(
            update={
                "status": "pending",
                "query_budget": next_budget,
                "retry_count": task.retry_count + 1,
            }
        )

    if action == "expand_fetch":
        next_budget = min(_MAX_FETCH_BUDGET, task.fetch_budget + 2)
        if outcome is not None:
            next_budget = min(_MAX_FETCH_BUDGET, max(next_budget, len(outcome.used_urls) + 2))
        if next_budget <= task.fetch_budget:
            return None
        return task.model_copy(
            update={
                "status": "pending",
                "fetch_budget": next_budget,
                "retry_count": task.retry_count + 1,
            }
        )

    return None


def _can_expand_queries(outcome: ResearchTaskOutcome) -> bool:
    return outcome.total_query_count > outcome.query_count


def _can_expand_fetch(outcome: ResearchTaskOutcome) -> bool:
    return outcome.search_hit_count > len(outcome.used_urls)


def _acquisition_retry_action(outcome: ResearchTaskOutcome) -> str:
    if _can_expand_fetch(outcome):
        return "expand_fetch"
    if _can_expand_queries(outcome):
        return "expand_queries"
    return "replan"


def _evidence_retry_action(outcome: ResearchTaskOutcome) -> str:
    if _can_expand_fetch(outcome):
        return "expand_fetch"
    if _can_expand_queries(outcome):
        return "expand_queries"
    return "replan"
