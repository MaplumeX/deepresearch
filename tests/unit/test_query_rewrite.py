from __future__ import annotations

import unittest

from app.config import Settings
from app.domain.models import ResearchRequest, ResearchTask
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

    def test_fallback_query_rewrite_covers_multiple_intents(self) -> None:
        queries = rewrite_queries(self.task, self.request, settings=self.settings)

        self.assertGreaterEqual(len(queries), 3)
        self.assertLessEqual(len(queries), 6)
        self.assertEqual(len(queries), len(set(query.query.casefold() for query in queries)))
        self.assertTrue(any(query.intent == "official" for query in queries))
        self.assertTrue(any(query.intent == "recent" for query in queries))
        self.assertTrue(any(query.intent == "risk" for query in queries))


if __name__ == "__main__":
    unittest.main()
