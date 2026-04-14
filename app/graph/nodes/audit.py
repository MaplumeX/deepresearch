from __future__ import annotations

from app.config import get_settings
from app.domain.models import QualityGateResult
from app.services.citations import find_missing_citations, has_citations


def citation_audit(state: dict) -> dict:
    warnings = list(state.get("warnings", []))
    draft_report = state.get("draft_report", "")
    sources = state.get("sources", {})

    if not draft_report.strip():
        warnings.append("Draft report is empty.")

    if state.get("findings") and not has_citations(draft_report):
        warnings.append("Draft report does not include inline citations.")

    missing = find_missing_citations(draft_report, sources)
    if missing:
        warnings.append(f"Draft report references unknown citations: {', '.join(missing)}")

    settings = get_settings()
    quality_gate = QualityGateResult.model_validate(state.get("quality_gate", {}))
    return {
        "warnings": warnings,
        "review_required": (
            bool(state.get("review_required", False))
            or quality_gate.requires_review
            or bool(missing)
            or settings.require_human_review
        ),
    }


def after_audit(state: dict) -> str:
    if state.get("review_required"):
        return "human_review"
    return "finalize"
