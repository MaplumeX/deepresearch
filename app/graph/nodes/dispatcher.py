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
            },
        )
        for task in tasks
    ]

