from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


def _read_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str
    planner_model: str
    synthesis_model: str
    llm_api_key: str | None
    llm_base_url: str | None
    tavily_api_key: str | None
    checkpoint_db_path: str
    fetch_timeout_seconds: float
    default_max_iterations: int
    default_max_parallel_tasks: int
    search_max_results: int
    require_human_review: bool
    enable_llm_planning: bool
    enable_llm_synthesis: bool


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "deep-research-agent"),
        planner_model=os.getenv("PLANNER_MODEL", "gpt-4.1-mini"),
        synthesis_model=os.getenv("SYNTHESIS_MODEL", "gpt-4.1-mini"),
        llm_api_key=os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),
        llm_base_url=os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL"),
        tavily_api_key=os.getenv("TAVILY_API_KEY"),
        checkpoint_db_path=os.getenv("CHECKPOINT_DB_PATH", "research.db"),
        fetch_timeout_seconds=float(os.getenv("FETCH_TIMEOUT_SECONDS", "15")),
        default_max_iterations=int(os.getenv("DEFAULT_MAX_ITERATIONS", "2")),
        default_max_parallel_tasks=int(os.getenv("DEFAULT_MAX_PARALLEL_TASKS", "3")),
        search_max_results=int(os.getenv("SEARCH_MAX_RESULTS", "3")),
        require_human_review=_read_bool("REQUIRE_HUMAN_REVIEW", False),
        enable_llm_planning=_read_bool("ENABLE_LLM_PLANNING", True),
        enable_llm_synthesis=_read_bool("ENABLE_LLM_SYNTHESIS", True),
    )
