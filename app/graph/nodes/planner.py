from __future__ import annotations

from app.config import get_settings
from app.domain.models import ResearchRequest
from app.services.planning import plan_research_tasks


def plan_research(state: dict) -> dict:
    request = ResearchRequest.model_validate(state["request"])
    settings = get_settings()
    tasks = plan_research_tasks(
        question=request.question,
        gaps=state.get("gaps", []),
        max_tasks=request.max_parallel_tasks,
        settings=settings,
    )
    return {
        "tasks": [task.model_dump() for task in tasks],
        "iteration_count": state.get("iteration_count", 0) + 1,
    }

