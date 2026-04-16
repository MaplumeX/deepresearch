from __future__ import annotations

import importlib.util
import unittest
from unittest.mock import patch

if importlib.util.find_spec("pydantic") is not None:
    from app.config import Settings
    from app.domain.models import CoverageRequirement, ResearchPlan, ResearchTask
    from app.graph.nodes.planner import plan_research
    from app.services.llm import LLMNotReadyError
    from app.services.planning import plan_research_tasks
else:
    Settings = None
    CoverageRequirement = None
    LLMNotReadyError = None
    plan_research = None
    ResearchPlan = None
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

    def test_plan_research_tasks_requires_llm(self) -> None:
        with self.assertRaises(LLMNotReadyError):
            plan_research_tasks(
                question="How do I build a deep research agent?",
                gaps=[],
                max_tasks=2,
                settings=self.settings,
            )

    def test_plan_research_tasks_returns_llm_plan(self) -> None:
        llm_plan = ResearchPlan(
            tasks=[
                ResearchTask(
                    task_id="task-1",
                    title="Recent evidence",
                    question="Q",
                    coverage_tags=["recent", "evidence"],
                )
            ],
            coverage_requirements=[
                CoverageRequirement(
                    requirement_id="recent-evidence",
                    title="Recent evidence",
                    description="Collect current support.",
                    coverage_tags=["recent", "examples"],
                )
            ],
        )

        with patch("app.services.planning._plan_with_llm", return_value=llm_plan):
            plan = plan_research_tasks(
                question="How do I build a deep research agent?",
                gaps=[],
                max_tasks=2,
                settings=self.settings,
            )

        self.assertEqual(plan.coverage_requirements[0].requirement_id, "recent-evidence")
        self.assertEqual(plan.coverage_requirements[0].coverage_tags, ["recent", "examples"])
        self.assertEqual(plan.tasks[0].coverage_tags, ["recent", "evidence"])

    def test_planner_node_assigns_iteration_scoped_task_ids(self) -> None:
        with patch("app.graph.nodes.planner.get_settings", return_value=self.settings), patch(
            "app.graph.nodes.planner.plan_research_tasks",
            return_value=ResearchPlan(
                tasks=[
                    ResearchTask(
                        task_id="task-1",
                        title="Recover search coverage",
                        question="Q",
                        coverage_tags=["recent", "evidence"],
                    )
                ],
                coverage_requirements=[
                    CoverageRequirement(
                        requirement_id="recent-evidence",
                        title="Recent evidence",
                        description="Collect current support.",
                        coverage_tags=["recent", "evidence"],
                    )
                ],
            ),
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
        self.assertEqual(result["coverage_requirements"][0]["requirement_id"], "recent-evidence")


if __name__ == "__main__":
    unittest.main()
