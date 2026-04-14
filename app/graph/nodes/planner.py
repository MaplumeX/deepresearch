from __future__ import annotations

from app.config import get_settings
from app.domain.models import ResearchRequest
from app.services.planning import plan_research_tasks


def plan_research(state: dict) -> dict:
    request = ResearchRequest.model_validate(state["request"])
    settings = get_settings()
    next_iteration = state.get("iteration_count", 0) + 1
    tasks = plan_research_tasks(
        question=request.question,
        gaps=state.get("gaps", []),
        max_tasks=request.max_parallel_tasks,
        settings=settings,
        memory=state.get("memory"),
    )
    serialized_tasks = []
    for index, task in enumerate(tasks, start=1):
        serialized_tasks.append(
            task.model_copy(update={"task_id": f"iter-{next_iteration}-task-{index}"}).model_dump()
        )
    return {
        "tasks": serialized_tasks,
        "iteration_count": next_iteration,
    }
