from __future__ import annotations


def finalize(state: dict) -> dict:
    final_report = state.get("final_report") or state.get("draft_report", "")
    final_structured_report = state.get("final_structured_report") or state.get("draft_structured_report", {})
    return {
        "final_report": final_report,
        "final_structured_report": final_structured_report,
    }
