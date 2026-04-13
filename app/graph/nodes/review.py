from __future__ import annotations

from langgraph.types import interrupt


def human_review(state: dict) -> dict:
    decision = interrupt(
        {
            "kind": "human_review",
            "draft_report": state.get("draft_report", ""),
            "warnings": state.get("warnings", []),
        }
    )
    final_report = state.get("draft_report", "")
    if isinstance(decision, dict):
        final_report = decision.get("edited_report") or final_report
    return {
        "final_report": final_report,
        "review_required": False,
    }

