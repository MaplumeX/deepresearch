from __future__ import annotations

from langgraph.types import Send


def dispatch_tasks(_: dict) -> dict:
    return {}


def route_research_tasks(state: dict):
    tasks = [
        task
        for task in state.get("tasks", [])
        if task.get("status", "pending") == "pending"
    ]
    if not tasks:
        return "merge_evidence"
    return [
        Send(
            "research_worker",
            {
                "request": state["request"],
                "task": task,
                "task_index": index,
                "task_total": len(tasks),
                "iteration_count": state.get("iteration_count"),
            },
        )
        for index, task in enumerate(tasks, start=1)
    ]
