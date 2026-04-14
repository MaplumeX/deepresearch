from __future__ import annotations

from app.config import get_settings
from app.domain.models import ConversationMemoryPayload, QualityGateResult, ResearchGap, ResearchRequest, ResearchTaskOutcome
from app.services.budgets import normalize_request_payload


def ingest_request(state: dict) -> dict:
    settings = get_settings()
    request_payload = normalize_request_payload(state.get("request", {}), settings)
    request = ResearchRequest.model_validate(request_payload)
    memory = ConversationMemoryPayload.model_validate(state.get("memory", {}))
    task_outcomes = [
        ResearchTaskOutcome.model_validate(item).model_dump()
        for item in state.get("task_outcomes", [])
    ]
    gaps = [
        ResearchGap.model_validate(item).model_dump()
        for item in state.get("gaps", [])
    ]
    quality_gate = QualityGateResult.model_validate(state.get("quality_gate", {}))
    return {
        "request": request.model_dump(),
        "memory": memory.model_dump(),
        "tasks": state.get("tasks", []),
        "raw_findings": state.get("raw_findings", []),
        "raw_source_batches": state.get("raw_source_batches", []),
        "task_outcomes": task_outcomes,
        "findings": state.get("findings", []),
        "sources": state.get("sources", {}),
        "gaps": gaps,
        "quality_gate": quality_gate.model_dump(),
        "warnings": state.get("warnings", []),
        "draft_report": state.get("draft_report", ""),
        "final_report": state.get("final_report", ""),
        "iteration_count": state.get("iteration_count", 0),
        "review_required": state.get("review_required", False),
    }
