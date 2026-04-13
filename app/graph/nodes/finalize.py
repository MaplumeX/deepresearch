from __future__ import annotations


def finalize(state: dict) -> dict:
    final_report = state.get("final_report") or state.get("draft_report", "")
    return {"final_report": final_report}

