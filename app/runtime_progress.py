from __future__ import annotations

from collections.abc import Callable
from typing import Any


ProgressListener = Callable[[dict[str, Any]], None]

_LISTENERS: dict[str, ProgressListener] = {}


def register_progress_listener(run_id: str, listener: ProgressListener | None) -> None:
    if listener is None:
        return
    _LISTENERS[run_id] = listener


def unregister_progress_listener(run_id: str, listener: ProgressListener | None) -> None:
    current = _LISTENERS.get(run_id)
    if listener is None or current is not listener:
        return
    _LISTENERS.pop(run_id, None)


def emit_progress(config: dict[str, Any] | None, payload: dict[str, Any]) -> None:
    run_id = _run_id_from_config(config)
    if run_id is None:
        return
    listener = _LISTENERS.get(run_id)
    if listener is None:
        return
    listener(payload)


def _run_id_from_config(config: dict[str, Any] | None) -> str | None:
    if not isinstance(config, dict):
        return None
    configurable = config.get("configurable")
    if not isinstance(configurable, dict):
        return None
    thread_id = configurable.get("thread_id")
    if not isinstance(thread_id, str) or not thread_id:
        return None
    return thread_id
