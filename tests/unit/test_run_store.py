from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.run_store import ResearchRunStore


class ResearchRunStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "runs.db"
        self.store = ResearchRunStore(str(self.db_path))
        self.store.initialize()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_and_list_runs(self) -> None:
        created = self.store.create_run(
            "run-1",
            {
                "question": "How do I build a deep research agent?",
                "output_language": "zh-CN",
            },
        )

        listed = self.store.list_runs()

        self.assertEqual(created.status, "queued")
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0].run_id, "run-1")
        self.assertEqual(listed[0].request.question, "How do I build a deep research agent?")

    def test_store_result_extracts_warnings(self) -> None:
        self.store.create_run(
            "run-2",
            {
                "question": "Question",
                "output_language": "zh-CN",
            },
        )

        updated = self.store.store_result(
            "run-2",
            "interrupted",
            {
                "draft_report": "# Draft",
                "warnings": ["Need manual review"],
                "__interrupt__": [{"kind": "human_review"}],
            },
        )

        self.assertEqual(updated.status, "interrupted")
        self.assertEqual(updated.warnings, ["Need manual review"])
        self.assertEqual(updated.result["draft_report"], "# Draft")


if __name__ == "__main__":
    unittest.main()
