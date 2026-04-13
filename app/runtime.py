from __future__ import annotations

from typing import Any

from langgraph.types import Command

from app.config import get_settings
from app.graph.builder import build_graph


def build_initial_state(request_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "request": request_payload,
        "tasks": [],
        "raw_findings": [],
        "raw_source_batches": [],
        "findings": [],
        "sources": {},
        "gaps": [],
        "warnings": [],
        "draft_report": "",
        "final_report": "",
        "iteration_count": 0,
        "review_required": False,
    }


async def run_research(request_payload: dict[str, Any], run_id: str) -> dict[str, Any]:
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    settings = get_settings()
    async with AsyncSqliteSaver.from_conn_string(settings.checkpoint_db_path) as checkpointer:
        graph = build_graph(checkpointer=checkpointer)
        return await graph.ainvoke(
            build_initial_state(request_payload),
            config={"configurable": {"thread_id": run_id}},
        )


async def resume_research(run_id: str, resume_payload: dict[str, Any]) -> dict[str, Any]:
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    settings = get_settings()
    async with AsyncSqliteSaver.from_conn_string(settings.checkpoint_db_path) as checkpointer:
        graph = build_graph(checkpointer=checkpointer)
        return await graph.ainvoke(
            Command(resume=resume_payload),
            config={"configurable": {"thread_id": run_id}},
        )

