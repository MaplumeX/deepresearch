from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def read_bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_env_file(path: str | Path) -> bool:
    env_path = Path(path)
    if not env_path.is_file():
        return False

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].strip()

        key, separator, value = line.partition("=")
        if not separator:
            continue

        key = key.strip()
        if not key:
            continue

        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        os.environ.setdefault(key, value)

    return True


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str
    planner_model: str
    synthesis_model: str
    llm_api_key: str | None
    llm_base_url: str | None
    tavily_api_key: str | None
    brave_api_key: str | None
    checkpoint_db_path: str
    runs_db_path: str
    fetch_timeout_seconds: float
    default_max_iterations: int
    default_max_parallel_tasks: int
    search_max_results: int
    require_human_review: bool
    enable_llm_planning: bool
    enable_llm_synthesis: bool
    synthesis_soft_char_limit: int = 90000
    synthesis_hard_char_limit: int = 110000
    synthesis_max_findings_per_call: int = 24
    synthesis_max_sources_per_call: int = 12


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "deep-research-agent"),
        planner_model=os.getenv("PLANNER_MODEL", "gpt-4.1-mini"),
        synthesis_model=os.getenv("SYNTHESIS_MODEL", "gpt-4.1-mini"),
        llm_api_key=os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),
        llm_base_url=os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL"),
        tavily_api_key=os.getenv("TAVILY_API_KEY"),
        brave_api_key=os.getenv("BRAVE_API_KEY"),
        checkpoint_db_path=os.getenv("CHECKPOINT_DB_PATH", "research.db"),
        runs_db_path=os.getenv("RUNS_DB_PATH", "research_runs.db"),
        fetch_timeout_seconds=float(os.getenv("FETCH_TIMEOUT_SECONDS", "15")),
        default_max_iterations=int(os.getenv("DEFAULT_MAX_ITERATIONS", "2")),
        default_max_parallel_tasks=int(os.getenv("DEFAULT_MAX_PARALLEL_TASKS", "3")),
        search_max_results=int(os.getenv("SEARCH_MAX_RESULTS", "3")),
        require_human_review=read_bool_env("REQUIRE_HUMAN_REVIEW", False),
        enable_llm_planning=read_bool_env("ENABLE_LLM_PLANNING", True),
        enable_llm_synthesis=read_bool_env("ENABLE_LLM_SYNTHESIS", True),
        synthesis_soft_char_limit=int(os.getenv("SYNTHESIS_SOFT_CHAR_LIMIT", "90000")),
        synthesis_hard_char_limit=int(os.getenv("SYNTHESIS_HARD_CHAR_LIMIT", "110000")),
        synthesis_max_findings_per_call=int(os.getenv("SYNTHESIS_MAX_FINDINGS_PER_CALL", "24")),
        synthesis_max_sources_per_call=int(os.getenv("SYNTHESIS_MAX_SOURCES_PER_CALL", "12")),
    )
