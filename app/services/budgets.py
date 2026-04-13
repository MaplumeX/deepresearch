from __future__ import annotations

from typing import Any

from app.config import Settings


def clamp_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(parsed, maximum))


def normalize_request_payload(payload: dict[str, Any], settings: Settings) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["max_iterations"] = clamp_int(
        normalized.get("max_iterations"),
        settings.default_max_iterations,
        1,
        5,
    )
    normalized["max_parallel_tasks"] = clamp_int(
        normalized.get("max_parallel_tasks"),
        settings.default_max_parallel_tasks,
        1,
        5,
    )
    return normalized

