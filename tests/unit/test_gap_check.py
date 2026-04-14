from __future__ import annotations

import unittest

from app.graph.nodes.gap_check import after_gap_check, gap_check


class GapCheckTest(unittest.TestCase):
    def test_gap_check_returns_structured_gap_and_replans_when_budget_exists(self) -> None:
        state = {
            "request": {
                "question": "How do we improve this worker?",
                "output_language": "en",
                "max_iterations": 3,
                "max_parallel_tasks": 2,
            },
            "tasks": [
                {"task_id": "iter-1-task-1", "title": "Evidence", "question": "Q"},
            ],
            "task_outcomes": [
                {
                    "task_id": "iter-1-task-1",
                    "title": "Evidence",
                    "quality_status": "failed",
                    "query_count": 2,
                    "search_hit_count": 0,
                    "acquired_content_count": 0,
                    "kept_source_count": 0,
                    "evidence_count": 0,
                    "host_count": 0,
                    "failure_reasons": ["no_search_hits"],
                }
            ],
            "warnings": [],
            "iteration_count": 1,
            "review_required": False,
        }

        result = gap_check(state)

        self.assertEqual(result["gaps"][0]["gap_type"], "retrieval_failure")
        self.assertEqual(result["quality_gate"]["should_replan"], True)
        self.assertEqual(after_gap_check(result), "plan_research")

    def test_gap_check_requires_review_when_budget_is_exhausted(self) -> None:
        state = {
            "request": {
                "question": "How do we improve this worker?",
                "output_language": "en",
                "max_iterations": 1,
                "max_parallel_tasks": 2,
            },
            "tasks": [
                {"task_id": "iter-1-task-1", "title": "Evidence", "question": "Q"},
            ],
            "task_outcomes": [
                {
                    "task_id": "iter-1-task-1",
                    "title": "Evidence",
                    "quality_status": "failed",
                    "query_count": 2,
                    "search_hit_count": 0,
                    "acquired_content_count": 0,
                    "kept_source_count": 0,
                    "evidence_count": 0,
                    "host_count": 0,
                    "failure_reasons": ["no_search_hits"],
                }
            ],
            "warnings": [],
            "iteration_count": 1,
            "review_required": False,
        }

        result = gap_check(state)

        self.assertEqual(result["quality_gate"]["should_replan"], False)
        self.assertEqual(result["quality_gate"]["requires_review"], True)
        self.assertEqual(after_gap_check(result), "synthesize_report")
        self.assertIn("Research quality gate did not pass before synthesis", result["warnings"][0])


if __name__ == "__main__":
    unittest.main()
