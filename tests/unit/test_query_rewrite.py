from __future__ import annotations

from dataclasses import replace
import unittest
from unittest.mock import patch

from app.config import Settings
from app.domain.models import ResearchQuery, ResearchRequest, ResearchTask
from app.services.llm import LLMNotReadyError, LLMOutputInvalidError
from app.services.query_rewrite import rewrite_queries


class QueryRewriteServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            app_name="test",
            planner_model="test-model",
            synthesis_model="test-model",
            llm_api_key=None,
            llm_base_url=None,
            tavily_api_key=None,
            brave_api_key=None,
            serper_api_key=None,
            checkpoint_db_path="test.db",
            runs_db_path="test-runs.db",
            fetch_timeout_seconds=1.0,
            default_max_iterations=2,
            default_max_parallel_tasks=3,
            search_max_results=3,
            require_human_review=False,
            enable_llm_planning=False,
            enable_llm_synthesis=False,
        )
        self.request = ResearchRequest(
            question="How should we improve deep research coverage?",
            scope="Focus on breadth, evidence diversity, and report structure",
            output_language="en",
        )
        self.task = ResearchTask(
            task_id="task-1",
            title="Coverage strategy",
            question="Improve deep research breadth and coverage strategy",
        )

    def test_query_rewrite_requires_llm(self) -> None:
        with self.assertRaises(LLMNotReadyError):
            rewrite_queries(self.task, self.request, settings=self.settings)

    def test_query_rewrite_requires_minimum_distinct_queries(self) -> None:
        ready_settings = replace(self.settings, llm_api_key="dummy-key", enable_llm_planning=True)
        with patch(
            "app.services.query_rewrite._rewrite_queries_with_llm",
            return_value=[
                ResearchQuery(query="same query", intent="baseline", priority=2),
                ResearchQuery(query="same query", intent="recent", priority=1),
            ],
        ):
            with self.assertRaises(LLMOutputInvalidError):
                rewrite_queries(self.task, self.request, settings=ready_settings)

    def test_query_rewrite_returns_distinct_queries_sorted_by_priority(self) -> None:
        ready_settings = replace(self.settings, llm_api_key="dummy-key", enable_llm_planning=True)
        with patch(
            "app.services.query_rewrite._rewrite_queries_with_llm",
            return_value=[
                ResearchQuery(query="examples", intent="example", priority=3),
                ResearchQuery(query="official docs", intent="official", priority=0),
                ResearchQuery(query="latest benchmarks", intent="recent", priority=1),
            ],
        ):
            queries = rewrite_queries(self.task, self.request, settings=ready_settings)

        self.assertEqual([query.query for query in queries], ["official docs", "latest benchmarks", "examples"])


if __name__ == "__main__":
    unittest.main()
