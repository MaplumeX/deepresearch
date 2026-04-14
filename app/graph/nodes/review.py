from __future__ import annotations

from langgraph.types import interrupt

from app.services.report_contract import derive_structured_report


def human_review(state: dict) -> dict:
    decision = interrupt(
        {
            "kind": "human_review",
            "draft_report": state.get("draft_report", ""),
            "draft_structured_report": state.get("draft_structured_report", {}),
            "warnings": state.get("warnings", []),
        }
    )
    final_report = state.get("draft_report", "")
    final_structured_report = state.get("draft_structured_report", {})
    if isinstance(decision, dict):
        final_report = decision.get("edited_report") or final_report
        if final_report:
            final_structured_report = derive_structured_report(
                markdown=final_report,
                sources=state.get("sources", {}),
                findings=state.get("findings", []),
                title_hint=state.get("draft_structured_report", {}).get("title", "Research Report"),
            ).model_dump()
    return {
        "final_report": final_report,
        "final_structured_report": final_structured_report,
        "review_required": False,
    }
