from langchain_core.runnables import RunnableConfig

from app.config import get_settings
from app.domain.models import ResearchRequest
from app.runtime_progress import emit_progress
from app.services.planning import plan_research_tasks
from app.services.research_progress import build_counts, build_progress_payload, count_completed_tasks


def plan_research(state: dict, config: RunnableConfig | None = None) -> dict:
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
    emit_progress(
        config,
        {
            "message": "Planning research tasks.",
            "progress": build_progress_payload(
                "planning",
                iteration=next_iteration,
                max_iterations=request.max_iterations,
                counts=build_counts(
                    planned_tasks=len(serialized_tasks),
                    completed_tasks=count_completed_tasks(state.get("task_outcomes", [])),
                    warnings=len(state.get("warnings", [])),
                ),
            ).model_dump(),
        },
    )
    return {
        "tasks": serialized_tasks,
        "iteration_count": next_iteration,
    }
