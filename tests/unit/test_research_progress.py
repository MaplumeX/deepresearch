from __future__ import annotations

import unittest

from app.domain.models import ResearchGap, ResearchTask
from app.services.research_progress import (
    build_gap_progress,
    build_progress_action,
    build_progress_payload,
    build_retry_task_progress,
)


class ResearchProgressServiceTest(unittest.TestCase):
    def test_build_gap_progress_marks_global_coverage_gap(self) -> None:
        summaries = build_gap_progress(
            [
                ResearchGap(
                    gap_type="coverage_gap",
                    task_id="coverage-risks-tradeoffs",
                    title="Cover risks and tradeoffs",
                    reason="Missing global risk coverage.",
                    retry_hint="Add risk analysis.",
                    severity="high",
                    retry_action="replan",
                )
            ]
        )

        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0].scope, "global")
        self.assertEqual(summaries[0].retry_action, "replan")

    def test_build_retry_task_progress_includes_pending_retry_tasks(self) -> None:
        retry_tasks = build_retry_task_progress(
            [
                ResearchTask(
                    task_id="task-1",
                    title="Recover search coverage",
                    question="Q",
                    status="pending",
                    retry_count=1,
                    query_budget=5,
                    fetch_budget=4,
                ),
                ResearchTask(
                    task_id="task-2",
                    title="Done task",
                    question="Q",
                    status="done",
                ),
            ],
            [
                ResearchGap(
                    gap_type="retrieval_failure",
                    task_id="task-1",
                    title="Recover search coverage",
                    reason="No ranked search results were available for this task.",
                    retry_hint="Broaden the query framing.",
                    severity="high",
                    retry_action="expand_queries",
                )
            ],
        )

        self.assertEqual(len(retry_tasks), 1)
        self.assertEqual(retry_tasks[0].task_id, "task-1")
        self.assertEqual(retry_tasks[0].retry_action, "expand_queries")
        self.assertEqual(retry_tasks[0].query_budget, 5)

    def test_build_progress_payload_includes_action_and_explainers(self) -> None:
        payload = build_progress_payload(
            "checking_gaps",
            action=build_progress_action(
                "targeted_retry",
                label="优先局部重试",
                detail="先扩查询和抓取预算。",
            ),
            gaps=build_gap_progress(
                [
                    ResearchGap(
                        gap_type="weak_evidence",
                        task_id="task-1",
                        title="Strengthen evidence",
                        reason="Only one evidence item was retained.",
                        retry_hint="Add another source.",
                        severity="medium",
                        retry_action="expand_fetch",
                    )
                ]
            ),
            retry_tasks=build_retry_task_progress(
                [
                    ResearchTask(
                        task_id="task-1",
                        title="Strengthen evidence",
                        question="Q",
                        status="pending",
                        retry_count=1,
                        query_budget=3,
                        fetch_budget=6,
                    )
                ],
                [
                    ResearchGap(
                        gap_type="weak_evidence",
                        task_id="task-1",
                        title="Strengthen evidence",
                        reason="Only one evidence item was retained.",
                        retry_hint="Add another source.",
                        severity="medium",
                        retry_action="expand_fetch",
                    )
                ],
            ),
        )

        self.assertEqual(payload.action.kind, "targeted_retry")
        self.assertEqual(payload.gaps[0].retry_action, "expand_fetch")
        self.assertEqual(payload.retry_tasks[0].fetch_budget, 6)


if __name__ == "__main__":
    unittest.main()
