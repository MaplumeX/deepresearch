from __future__ import annotations

from pydantic import ValidationError

from app.config import get_settings
from app.domain.models import QualityGateResult, StructuredReport
from app.services.citations import find_missing_citations, has_citations
from app.services.report_contract import derive_structured_report


def citation_audit(state: dict) -> dict:
    warnings = list(state.get("warnings", []))
    draft_report = state.get("draft_report", "")
    sources = state.get("sources", {})
    findings = state.get("findings", [])
    draft_structured_report = _read_structured_report(
        state.get("draft_structured_report"),
        draft_report,
        sources,
        findings,
    )

    if not draft_report.strip():
        warnings.append("Draft report is empty.")

    if findings and not has_citations(draft_report):
        warnings.append("Draft report does not include inline citations.")

    missing = find_missing_citations(draft_report, sources)
    if missing:
        warnings.append(f"Draft report references unknown citations: {', '.join(missing)}")

    structural_warnings = _validate_structured_report(draft_structured_report, findings)
    for warning in structural_warnings:
        if warning not in warnings:
            warnings.append(warning)

    settings = get_settings()
    quality_gate = QualityGateResult.model_validate(state.get("quality_gate", {}))
    requires_review = bool(missing) or bool(_blocking_structural_warnings(structural_warnings))
    return {
        "warnings": warnings,
        "review_required": (
            bool(state.get("review_required", False))
            or quality_gate.requires_review
            or requires_review
            or settings.require_human_review
        ),
    }


def after_audit(state: dict) -> str:
    if state.get("review_required"):
        return "human_review"
    return "finalize"


def _read_structured_report(
    value: object,
    draft_report: str,
    sources: dict[str, dict],
    findings: list[dict],
) -> StructuredReport:
    if isinstance(value, dict) and value:
        try:
            return StructuredReport.model_validate(value)
        except ValidationError:
            pass
    return derive_structured_report(
        markdown=draft_report,
        sources=sources,
        findings=findings,
    )


def _validate_structured_report(report: StructuredReport, findings: list[dict]) -> list[str]:
    warnings: list[str] = []
    if findings and not report.sections:
        warnings.append("Structured report does not include any sections.")
        return warnings

    summary_section = next(
        (section for section in report.sections if section.heading.casefold() == "executive summary"),
        None,
    )
    if findings and summary_section is not None and not summary_section.cited_source_ids:
        warnings.append("Executive summary does not include inline citations.")

    for section in report.sections:
        if section.heading.casefold() in {"conversation context", "sources", "executive summary"}:
            continue
        if findings and section.body_markdown.strip() and not section.cited_source_ids:
            warnings.append(f"Section '{section.heading}' does not include inline citations.")

    extracted = report.cited_source_ids
    indexed = [entry.source_id for entry in report.citation_index]
    if extracted and sorted(extracted) != sorted(indexed):
        warnings.append("Structured report citation index is out of sync with cited sources.")
    return warnings


def _blocking_structural_warnings(warnings: list[str]) -> list[str]:
    return [
        warning
        for warning in warnings
        if warning.endswith("does not include inline citations.")
        or warning == "Structured report citation index is out of sync with cited sources."
        or warning == "Structured report does not include any sections."
    ]
