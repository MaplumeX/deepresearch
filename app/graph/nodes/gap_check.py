from __future__ import annotations


def identify_research_gaps(tasks: list[dict], findings: list[dict]) -> list[str]:
    findings_by_task: dict[str, int] = {}
    for finding in findings:
        task_id = str(finding.get("task_id", ""))
        findings_by_task[task_id] = findings_by_task.get(task_id, 0) + 1

    gaps: list[str] = []
    for task in tasks:
        if findings_by_task.get(task["task_id"], 0) == 0:
            gaps.append(f"No evidence collected for task: {task['title']}")

    unique_sources = {finding.get("source_id") for finding in findings if finding.get("source_id")}
    if findings and len(unique_sources) < 2:
        gaps.append("Need corroboration from additional independent sources.")

    return gaps


def gap_check(state: dict) -> dict:
    return {
        "gaps": identify_research_gaps(
            state.get("tasks", []),
            state.get("findings", []),
        )
    }


def after_gap_check(state: dict) -> str:
    request = state["request"]
    has_budget = state.get("iteration_count", 0) < request["max_iterations"]
    if state.get("gaps") and has_budget:
        return "plan_research"
    return "synthesize_report"

