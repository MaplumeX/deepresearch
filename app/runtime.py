from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import asdict, is_dataclass
from typing import Any

from langgraph.types import Command
from pydantic import BaseModel

from app.config import get_settings
from app.domain.models import ConversationMemoryPayload, QualityGateResult
from app.graph.builder import build_graph
from app.runtime_progress import register_progress_listener, unregister_progress_listener


def build_initial_state(
    request_payload: dict[str, Any],
    memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "request": request_payload,
        "memory": ConversationMemoryPayload.model_validate(memory or {}).model_dump(),
        "tasks": [],
        "raw_findings": [],
        "raw_source_batches": [],
        "task_outcomes": [],
        "findings": [],
        "sources": {},
        "gaps": [],
        "quality_gate": QualityGateResult().model_dump(),
        "warnings": [],
        "draft_report": "",
        "draft_structured_report": {},
        "final_report": "",
        "final_structured_report": {},
        "iteration_count": 0,
        "review_required": False,
    }


async def run_research(
    request_payload: dict[str, Any],
    run_id: str,
    memory: dict[str, Any] | None = None,
    on_progress=None,
) -> dict[str, Any]:
    settings = get_settings()
    config = {"configurable": {"thread_id": run_id}}
    async with _open_checkpointer(settings.checkpoint_db_path) as checkpointer:
        graph = build_graph(checkpointer=checkpointer)
        register_progress_listener(run_id, on_progress)
        try:
            result = await graph.ainvoke(
                build_initial_state(request_payload, memory),
                config=config,
            )
            return await _read_graph_snapshot(graph, config, result)
        finally:
            unregister_progress_listener(run_id, on_progress)

async def resume_research(run_id: str, resume_payload: dict[str, Any], on_progress=None) -> dict[str, Any]:
    settings = get_settings()
    config = {"configurable": {"thread_id": run_id}}
    async with _open_checkpointer(settings.checkpoint_db_path) as checkpointer:
        graph = build_graph(checkpointer=checkpointer)
        register_progress_listener(run_id, on_progress)
        try:
            result = await graph.ainvoke(
                Command(resume=resume_payload),
                config=config,
            )
            return await _read_graph_snapshot(graph, config, result)
        finally:
            unregister_progress_listener(run_id, on_progress)


@asynccontextmanager
async def _open_checkpointer(checkpoint_db_path: str):
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    _ensure_aiosqlite_connection_compatibility()
    async with AsyncSqliteSaver.from_conn_string(checkpoint_db_path) as checkpointer:
        yield checkpointer


def _ensure_aiosqlite_connection_compatibility() -> None:
    import aiosqlite

    if hasattr(aiosqlite.Connection, "is_alive"):
        return

    # langgraph-checkpoint-sqlite still probes `is_alive()` on the connection.
    def is_alive(connection: aiosqlite.Connection) -> bool:
        worker = getattr(connection, "_thread", None)
        if worker is not None and hasattr(worker, "is_alive"):
            return bool(worker.is_alive())
        if not bool(getattr(connection, "_running", False)):
            return False
        return getattr(connection, "_connection", None) is not None

    aiosqlite.Connection.is_alive = is_alive


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
