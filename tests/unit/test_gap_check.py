from __future__ import annotations

import unittest

from app.graph.nodes.gap_check import identify_research_gaps


class GapCheckTest(unittest.TestCase):
    def test_reports_tasks_without_findings(self) -> None:
        tasks = [
            {"task_id": "task-1", "title": "Scope"},
            {"task_id": "task-2", "title": "Evidence"},
        ]
        findings = [{"task_id": "task-1", "source_id": "S1"}]
        gaps = identify_research_gaps(tasks, findings)
        self.assertIn("No evidence collected for task: Evidence", gaps)

    def test_reports_need_for_corroboration(self) -> None:
        tasks = [{"task_id": "task-1", "title": "Scope"}]
        findings = [{"task_id": "task-1", "source_id": "S1"}]
        gaps = identify_research_gaps(tasks, findings)
        self.assertIn("Need corroboration from additional independent sources.", gaps)


if __name__ == "__main__":
    unittest.main()

