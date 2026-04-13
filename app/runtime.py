from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from langgraph.types import Command
from pydantic import BaseModel

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
    config = {"configurable": {"thread_id": run_id}}
    async with AsyncSqliteSaver.from_conn_string(settings.checkpoint_db_path) as checkpointer:
        graph = build_graph(checkpointer=checkpointer)
        result = await graph.ainvoke(
            build_initial_state(request_payload),
            config=config,
        )
        return await _read_graph_snapshot(graph, config, result)


async def resume_research(run_id: str, resume_payload: dict[str, Any]) -> dict[str, Any]:
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    settings = get_settings()
    config = {"configurable": {"thread_id": run_id}}
    async with AsyncSqliteSaver.from_conn_string(settings.checkpoint_db_path) as checkpointer:
        graph = build_graph(checkpointer=checkpointer)
        result = await graph.ainvoke(
            Command(resume=resume_payload),
            config=config,
        )
        return await _read_graph_snapshot(graph, config, result)


async def _read_graph_snapshot(graph, config: dict[str, Any], raw_result: dict[str, Any]) -> dict[str, Any]:
    snapshot = {}
    if hasattr(graph, "aget_state"):
        state = await graph.aget_state(config)
        if state is not None and getattr(state, "values", None):
            snapshot = _json_safe(state.values)

    if "__interrupt__" in raw_result:
        snapshot["__interrupt__"] = _json_safe(raw_result["__interrupt__"])

    if snapshot:
        return snapshot
    return _json_safe(raw_result)


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, default=_json_default))


def _json_default(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "value"):
        return getattr(value, "value")
    return str(value)
