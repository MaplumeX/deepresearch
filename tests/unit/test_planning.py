from __future__ import annotations

import importlib.util
import unittest

if importlib.util.find_spec("pydantic") is not None:
    from app.config import Settings
    from app.services.planning import plan_research_tasks
else:
    Settings = None
    plan_research_tasks = None


@unittest.skipUnless(Settings is not None, "pydantic is not installed in the current environment")
class PlanningServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            app_name="test",
            planner_model="test-model",
            synthesis_model="test-model",
            openai_api_key=None,
            tavily_api_key=None,
            checkpoint_db_path="test.db",
            fetch_timeout_seconds=1.0,
            default_max_iterations=2,
            default_max_parallel_tasks=3,
            search_max_results=3,
            require_human_review=False,
            enable_llm_planning=False,
            enable_llm_synthesis=False,
        )

    def test_fallback_planner_limits_task_count(self) -> None:
        tasks = plan_research_tasks(
            question="How do I build a deep research agent?",
            gaps=[],
            max_tasks=2,
            settings=self.settings,
        )
        self.assertEqual(len(tasks), 2)
        self.assertEqual(tasks[0].task_id, "task-1")

    def test_gaps_are_translated_to_follow_up_tasks(self) -> None:
        tasks = plan_research_tasks(
            question="How do I build a deep research agent?",
            gaps=["Need primary sources"],
            max_tasks=3,
            settings=self.settings,
        )
        self.assertEqual(tasks[0].title, "Resolve gap: Need primary sources")


if __name__ == "__main__":
    unittest.main()
