from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

from app.domain.models import (
    QualityGateResult,
    ResearchGap,
    ResearchTask,
    ResearchTaskOutcome,
)


def build_task_outcome(
    task: ResearchTask,
    *,
    query_count: int,
    search_hit_count: int,
    acquired_content_count: int,
    kept_source_count: int,
    evidence_count: int,
    source_urls: list[str],
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
        search_hit_count=search_hit_count,
        acquired_content_count=acquired_content_count,
        kept_source_count=kept_source_count,
        evidence_count=evidence_count,
        host_count=host_count,
        failure_reasons=failure_reasons,
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
) -> list[ResearchGap]:
    findings = findings or []
    sources = sources or {}
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
                )
            )

        gaps.extend(
            _build_coverage_gaps_for_task(
                task,
                task_findings=findings_by_task.get(task.task_id, []),
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
        )

    if "content_acquisition_failed" in outcome.failure_reasons:
        return ResearchGap(
            gap_type="retrieval_failure",
            task_id=task.task_id,
            title=f"Recover source acquisition for {task.title}",
            reason="Search hits were found, but no usable content could be acquired.",
            retry_hint=f"Look for alternative URLs or source types that can provide readable content for {task.title}.",
            severity="high",
        )

    if "insufficient_content" in outcome.failure_reasons:
        return ResearchGap(
            gap_type="missing_evidence",
            task_id=task.task_id,
            title=f"Recover substantive content for {task.title}",
            reason="Acquired pages were too thin or too noisy to keep as usable sources.",
            retry_hint=f"Prioritize pages with substantive text, data, or direct claims about {task.title}.",
            severity="high",
        )

    return ResearchGap(
        gap_type="missing_evidence",
        task_id=task.task_id,
        title=f"Recover extractable evidence for {task.title}",
        reason="Usable sources were kept, but no evidence claim was extracted.",
        retry_hint=f"Find sources that state concrete facts, numbers, or explicit conclusions about {task.title}.",
        severity="high",
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
