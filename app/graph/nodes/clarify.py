from __future__ import annotations

from app.runtime_progress import emit_progress
from app.services.research_progress import build_progress_payload


def clarify_scope(state: dict, config: dict | None = None) -> dict:
    request = dict(state["request"])
    emit_progress(
        config,
        {
            "message": "Clarifying research scope.",
            "progress": build_progress_payload(
                "clarifying_scope",
                max_iterations=request.get("max_iterations"),
            ).model_dump(),
        },
    )
    if not request.get("scope"):
        request["scope"] = "Investigate the question, collect evidence, and produce a cited markdown report."
    return {"request": request}
