from __future__ import annotations

from app.config import get_settings
from app.domain.models import ResearchRequest
from app.services.budgets import normalize_request_payload


def ingest_request(state: dict) -> dict:
    settings = get_settings()
    request_payload = normalize_request_payload(state.get("request", {}), settings)
    request = ResearchRequest.model_validate(request_payload)
    return {
        "request": request.model_dump(),
        "tasks": state.get("tasks", []),
        "raw_findings": state.get("raw_findings", []),
        "raw_source_batches": state.get("raw_source_batches", []),
        "findings": state.get("findings", []),
        "sources": state.get("sources", {}),
        "gaps": state.get("gaps", []),
        "warnings": state.get("warnings", []),
        "draft_report": state.get("draft_report", ""),
        "final_report": state.get("final_report", ""),
        "iteration_count": state.get("iteration_count", 0),
        "review_required": state.get("review_required", False),
    }

