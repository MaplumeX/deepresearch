from __future__ import annotations

from app.config import get_settings
from app.services.synthesis import synthesize_report


def synthesize_report_node(state: dict) -> dict:
    report = synthesize_report(
        question=state["request"]["question"],
        tasks=state.get("tasks", []),
        findings=state.get("findings", []),
        sources=state.get("sources", {}),
        settings=get_settings(),
        memory=state.get("memory"),
    )
    return {
        "draft_report": report.markdown,
    }
