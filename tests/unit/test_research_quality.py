from __future__ import annotations

import unittest

from app.domain.models import CoverageRequirement, ResearchTask
from app.services.research_quality import (
    build_retry_tasks,
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
            total_query_count=4,
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
            total_query_count=6,
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
        self.assertEqual(gaps[0].retry_action, "expand_queries")

    def test_identify_research_gaps_reports_low_source_diversity_for_weak_task(self) -> None:
        task = ResearchTask(task_id="task-1", title="Evidence", question="Q")
        outcome = build_task_outcome(
            task,
            query_count=3,
            total_query_count=6,
            search_hit_count=4,
            acquired_content_count=2,
            kept_source_count=2,
            evidence_count=2,
            source_urls=[
                "https://example.com/a",
                "https://example.com/b",
            ],
            used_urls=["https://example.com/a", "https://example.com/b"],
        )

        gaps = identify_research_gaps([task], [outcome])

        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0].gap_type, "low_source_diversity")
        self.assertEqual(gaps[0].retry_action, "expand_fetch")

    def test_quality_gate_requires_review_when_budget_is_exhausted(self) -> None:
        task = ResearchTask(task_id="task-1", title="Evidence", question="Q")
        outcome = build_task_outcome(
            task,
            query_count=1,
            total_query_count=1,
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

    def test_identify_research_gaps_reports_coverage_gaps(self) -> None:
        task = ResearchTask(task_id="task-1", title="Coverage", question="Q")
        outcome = build_task_outcome(
            task,
            query_count=3,
            total_query_count=3,
            search_hit_count=4,
            acquired_content_count=2,
            kept_source_count=2,
            evidence_count=2,
            source_urls=[
                "https://example.com/a",
                "https://another.example.com/b",
            ],
        )

        gaps = identify_research_gaps(
            [task],
            [outcome],
            findings=[
                {
                    "task_id": "task-1",
                    "claim": "Deep research coordinates multiple worker stages.",
                    "source_id": "S1",
                    "evidence_type": "fact",
                },
                {
                    "task_id": "task-1",
                    "claim": "It merges evidence before synthesis.",
                    "source_id": "S2",
                    "evidence_type": "fact",
                },
            ],
            sources={
                "S1": {"url": "https://example.com/a", "metadata": {}},
                "S2": {"url": "https://another.example.com/b", "metadata": {}},
            },
        )

        titles = {gap.title for gap in gaps if gap.gap_type == "coverage_gap"}
        self.assertIn("Add recent evidence for Coverage", titles)
        self.assertIn("Add examples or concrete data for Coverage", titles)
        self.assertIn("Add risks or limitations for Coverage", titles)

    def test_build_retry_tasks_expands_query_budget_for_retryable_gap(self) -> None:
        task = ResearchTask(task_id="task-1", title="Evidence", question="Q", query_budget=3)
        outcome = build_task_outcome(
            task,
            query_count=3,
            total_query_count=6,
            search_hit_count=0,
            acquired_content_count=0,
            kept_source_count=0,
            evidence_count=0,
            source_urls=[],
        )
        gaps = identify_research_gaps([task], [outcome])

        retried = build_retry_tasks([task], [outcome], gaps)

        self.assertEqual(len(retried), 1)
        self.assertEqual(retried[0].status, "pending")
        self.assertEqual(retried[0].query_budget, 5)
        self.assertEqual(retried[0].retry_count, 1)

    def test_identify_research_gaps_reports_global_coverage_gaps(self) -> None:
        task = ResearchTask(
            task_id="task-1",
            title="Scope",
            question="Q",
            coverage_tags=["scope", "definitions"],
        )
        outcome = build_task_outcome(
            task,
            query_count=2,
            total_query_count=2,
            search_hit_count=3,
            acquired_content_count=2,
            kept_source_count=2,
            evidence_count=2,
            source_urls=[
                "https://example.com/a",
                "https://another.example.com/b",
            ],
        )

        gaps = identify_research_gaps(
            [task],
            [outcome],
            findings=[
                {
                    "task_id": "task-1",
                    "claim": "Deep research defines a planning scope.",
                    "source_id": "S1",
                    "evidence_type": "definition",
                }
            ],
            sources={
                "S1": {"url": "https://example.com/a", "metadata": {}},
            },
            coverage_requirements=[
                CoverageRequirement(
                    requirement_id="scope-terminology",
                    title="Scope and terminology",
                    description="Clarify definitions and scope.",
                    coverage_tags=["scope", "definitions"],
                ),
                CoverageRequirement(
                    requirement_id="risks-tradeoffs",
                    title="Risks and tradeoffs",
                    description="Explain risks and tradeoffs.",
                    coverage_tags=["risks", "tradeoffs"],
                ),
            ],
        )

        coverage_gap_ids = {gap.task_id for gap in gaps if gap.gap_type == "coverage_gap"}
        self.assertIn("coverage-risks-tradeoffs", coverage_gap_ids)

    def test_identify_research_gaps_satisfies_global_coverage_when_requirement_has_matching_evidence(self) -> None:
        task = ResearchTask(
            task_id="task-1",
            title="Risks",
            question="Q",
            coverage_tags=["risks", "tradeoffs"],
        )
        outcome = build_task_outcome(
            task,
            query_count=2,
            total_query_count=2,
            search_hit_count=3,
            acquired_content_count=2,
            kept_source_count=2,
            evidence_count=2,
            source_urls=[
                "https://example.com/a",
                "https://another.example.com/b",
            ],
        )

        gaps = identify_research_gaps(
            [task],
            [outcome],
            findings=[
                {
                    "task_id": "task-1",
                    "claim": "A major tradeoff is latency versus coverage.",
                    "source_id": "S1",
                    "evidence_type": "comparison",
                },
                {
                    "task_id": "task-1",
                    "claim": "A failure mode is missing source diversity.",
                    "source_id": "S2",
                    "evidence_type": "risk",
                },
            ],
            sources={
                "S1": {"url": "https://example.com/a", "metadata": {}},
                "S2": {"url": "https://another.example.com/b", "metadata": {}},
            },
            coverage_requirements=[
                CoverageRequirement(
                    requirement_id="risks-tradeoffs",
                    title="Risks and tradeoffs",
                    description="Explain risks and tradeoffs.",
                    coverage_tags=["risks", "tradeoffs"],
                )
            ],
        )

        self.assertFalse(any(gap.task_id == "coverage-risks-tradeoffs" for gap in gaps))


if __name__ == "__main__":
    unittest.main()
