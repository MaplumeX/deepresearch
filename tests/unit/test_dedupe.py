from __future__ import annotations

import unittest

from app.services.dedupe import dedupe_findings


class DedupeServiceTest(unittest.TestCase):
    def test_keeps_highest_scoring_duplicate(self) -> None:
        findings = [
            {
                "task_id": "task-1",
                "source_id": "S1",
                "claim": "Same claim",
                "confidence": 0.2,
                "relevance_score": 0.2,
            },
            {
                "task_id": "task-1",
                "source_id": "S1",
                "claim": "Same claim",
                "confidence": 0.6,
                "relevance_score": 0.4,
            },
        ]
        deduped = dedupe_findings(findings)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0]["confidence"], 0.6)

    def test_keeps_distinct_sources(self) -> None:
        findings = [
            {"task_id": "task-1", "source_id": "S1", "claim": "Claim", "confidence": 0.5, "relevance_score": 0.5},
            {"task_id": "task-1", "source_id": "S2", "claim": "Claim", "confidence": 0.5, "relevance_score": 0.5},
        ]
        deduped = dedupe_findings(findings)
        self.assertEqual(len(deduped), 2)


if __name__ == "__main__":
    unittest.main()

