from __future__ import annotations

import importlib.util
import unittest
from unittest.mock import patch

if importlib.util.find_spec("pydantic") is not None:
    from app.config import Settings
    from app.graph.nodes.planner import plan_research
    from app.domain.models import ResearchTask
    from app.services.planning import plan_research_tasks
else:
    Settings = None
    plan_research = None
    ResearchTask = None
    plan_research_tasks = None


@unittest.skipUnless(Settings is not None, "pydantic is not installed in the current environment")
class PlanningServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            app_name="test",
            planner_model="test-model",
            synthesis_model="test-model",
            llm_api_key=None,
            llm_base_url=None,
            tavily_api_key=None,
            brave_api_key=None,
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
            gaps=[
                {
                    "gap_type": "retrieval_failure",
                    "task_id": "iter-1-task-1",
                    "title": "Recover search coverage for primary sources",
                    "reason": "No ranked search results were available for this task.",
                    "retry_hint": "Broaden the search framing and look for official or primary sources.",
                    "severity": "high",
                }
            ],
            max_tasks=3,
            settings=self.settings,
        )
        self.assertEqual(tasks[0].title, "Recover search coverage for primary sources")
        self.assertIn("Retry hint:", tasks[0].question)

    def test_fallback_planner_includes_memory_context_in_task_question(self) -> None:
        tasks = plan_research_tasks(
            question="Can you continue this?",
            gaps=[],
            max_tasks=1,
            settings=self.settings,
            memory={
                "rolling_summary": "Earlier research compared LangGraph and LangChain roles.",
                "recent_turns": [
                    {
                        "run_id": "run-1",
                        "question": "How does the graph work?",
                        "answer_digest": "It plans, runs workers, merges evidence, and synthesizes a report.",
                        "status": "completed",
                        "created_at": "2026-04-13T00:00:00+00:00",
                    }
                ],
                "key_facts": [],
                "open_questions": [],
            },
        )
        self.assertIn("Conversation context:", tasks[0].question)

    def test_planner_node_assigns_iteration_scoped_task_ids(self) -> None:
        with patch("app.graph.nodes.planner.get_settings", return_value=self.settings), patch(
            "app.graph.nodes.planner.plan_research_tasks",
            return_value=[
                ResearchTask(
                    task_id="task-1",
                    title="Recover search coverage",
                    question="Q",
                )
            ],
        ):
            result = plan_research(
                {
                    "request": {
                        "question": "How do I build a deep research agent?",
                        "output_language": "en",
                        "max_iterations": 3,
                        "max_parallel_tasks": 2,
                    },
                    "gaps": [],
                    "memory": {},
                    "iteration_count": 1,
                }
            )

        self.assertEqual(result["iteration_count"], 2)
        self.assertEqual(result["tasks"][0]["task_id"], "iter-2-task-1")


if __name__ == "__main__":
    unittest.main()
