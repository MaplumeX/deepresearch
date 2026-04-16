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
                    "total_query_count": 6,
                    "search_hit_count": 0,
                    "acquired_content_count": 0,
                    "kept_source_count": 0,
                    "evidence_count": 0,
                    "host_count": 0,
                    "failure_reasons": ["no_search_hits"],
                    "executed_queries": ["Q", "Q official"],
                    "used_urls": [],
                    "stage_status": {"search_and_rank": "failed"},
                }
            ],
            "warnings": [],
            "iteration_count": 1,
            "review_required": False,
        }

        result = gap_check(state)

        self.assertEqual(result["gaps"][0]["gap_type"], "retrieval_failure")
        self.assertEqual(result["quality_gate"]["should_replan"], False)
        self.assertEqual(result["tasks"][0]["status"], "pending")
        self.assertEqual(result["tasks"][0]["query_budget"], 5)
        self.assertEqual(after_gap_check(result), "dispatch_tasks")

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
                    "total_query_count": 2,
                    "search_hit_count": 0,
                    "acquired_content_count": 0,
                    "kept_source_count": 0,
                    "evidence_count": 0,
                    "host_count": 0,
                    "failure_reasons": ["no_search_hits"],
                    "executed_queries": ["Q", "Q official"],
                    "used_urls": [],
                    "stage_status": {"search_and_rank": "failed"},
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

    def test_gap_check_replans_when_global_coverage_gap_remains(self) -> None:
        state = {
            "request": {
                "question": "How do we improve this worker?",
                "output_language": "en",
                "max_iterations": 3,
                "max_parallel_tasks": 2,
            },
            "tasks": [
                {
                    "task_id": "iter-1-task-1",
                    "title": "Scope",
                    "question": "Q",
                    "coverage_tags": ["scope", "definitions"],
                },
            ],
            "coverage_requirements": [
                {
                    "requirement_id": "scope-terminology",
                    "title": "Scope and terminology",
                    "description": "Clarify scope and terms.",
                    "coverage_tags": ["scope", "definitions"],
                },
                {
                    "requirement_id": "risks-tradeoffs",
                    "title": "Risks and tradeoffs",
                    "description": "Explain risks and tradeoffs.",
                    "coverage_tags": ["risks", "tradeoffs"],
                },
            ],
            "task_outcomes": [
                {
                    "task_id": "iter-1-task-1",
                    "title": "Scope",
                    "quality_status": "ok",
                    "query_count": 2,
                    "total_query_count": 2,
                    "search_hit_count": 3,
                    "acquired_content_count": 2,
                    "kept_source_count": 2,
                    "evidence_count": 2,
                    "host_count": 2,
                    "failure_reasons": [],
                    "executed_queries": ["Q", "Q terminology"],
                    "used_urls": ["https://example.com/a", "https://another.example.com/b"],
                    "stage_status": {"emit_results": "ok"},
                }
            ],
            "findings": [
                {
                    "task_id": "iter-1-task-1",
                    "claim": "The worker has a defined execution scope.",
                    "source_id": "S1",
                    "evidence_type": "definition",
                },
                {
                    "task_id": "iter-1-task-1",
                    "claim": "The worker runs through fixed stages.",
                    "source_id": "S2",
                    "evidence_type": "fact",
                },
            ],
            "sources": {
                "S1": {"url": "https://example.com/a", "metadata": {}},
                "S2": {"url": "https://another.example.com/b", "metadata": {}},
            },
            "warnings": [],
            "iteration_count": 1,
            "review_required": False,
        }

        result = gap_check(state)

        self.assertTrue(any(gap["task_id"] == "coverage-risks-tradeoffs" for gap in result["gaps"]))
        self.assertEqual(result["quality_gate"]["should_replan"], True)
        self.assertEqual(after_gap_check(result), "plan_research")


if __name__ == "__main__":
    unittest.main()
