from __future__ import annotations

import unittest

from app.domain.models import ResearchTask
from app.services.research_quality import (
    build_task_outcome,
    evaluate_quality_gate,
    format_quality_gate_warning,
    identify_research_gaps,
)


class ResearchQualityServiceTest(unittest.TestCase):
    def test_build_task_outcome_marks_failed_when_no_search_hits(self) -> None:
        outcome = build_task_outcome(
            ResearchTask(task_id="task-1", title="Scope", question="Q"),
            query_count=2,
            search_hit_count=0,
            acquired_content_count=0,
            kept_source_count=0,
            evidence_count=0,
            source_urls=[],
        )

        self.assertEqual(outcome.quality_status, "failed")
        self.assertIn("no_search_hits", outcome.failure_reasons)

    def test_identify_research_gaps_prefers_retrieval_failure_for_failed_task(self) -> None:
        task = ResearchTask(task_id="task-1", title="Evidence", question="Q")
        outcome = build_task_outcome(
            task,
            query_count=3,
            search_hit_count=0,
            acquired_content_count=0,
            kept_source_count=0,
            evidence_count=0,
            source_urls=[],
        )

        gaps = identify_research_gaps([task], [outcome])

        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0].gap_type, "retrieval_failure")
        self.assertIn("Recover search coverage", gaps[0].title)

    def test_identify_research_gaps_reports_low_source_diversity_for_weak_task(self) -> None:
        task = ResearchTask(task_id="task-1", title="Evidence", question="Q")
        outcome = build_task_outcome(
            task,
            query_count=3,
            search_hit_count=4,
            acquired_content_count=2,
            kept_source_count=2,
            evidence_count=2,
            source_urls=[
                "https://example.com/a",
                "https://example.com/b",
            ],
        )

        gaps = identify_research_gaps([task], [outcome])

        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0].gap_type, "low_source_diversity")

    def test_quality_gate_requires_review_when_budget_is_exhausted(self) -> None:
        task = ResearchTask(task_id="task-1", title="Evidence", question="Q")
        outcome = build_task_outcome(
            task,
            query_count=1,
            search_hit_count=0,
            acquired_content_count=0,
            kept_source_count=0,
            evidence_count=0,
            source_urls=[],
        )
        gaps = identify_research_gaps([task], [outcome])

        gate = evaluate_quality_gate(gaps, has_iteration_budget=False)

        self.assertFalse(gate.passed)
        self.assertFalse(gate.should_replan)
        self.assertTrue(gate.requires_review)
        self.assertIn("Recover search coverage", format_quality_gate_warning(gate))


if __name__ == "__main__":
    unittest.main()
