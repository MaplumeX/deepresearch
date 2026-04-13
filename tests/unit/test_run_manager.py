from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.config import Settings
from app.run_manager import InvalidRunStateError, ResearchRunManager


class ResearchRunManagerTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        base_path = Path(self.temp_dir.name)
        self.settings = Settings(
            app_name="test",
            planner_model="test-model",
            synthesis_model="test-model",
            llm_api_key=None,
            llm_base_url=None,
            tavily_api_key=None,
            checkpoint_db_path=str(base_path / "checkpoint.db"),
            runs_db_path=str(base_path / "runs.db"),
            fetch_timeout_seconds=1.0,
            default_max_iterations=2,
            default_max_parallel_tasks=3,
            search_max_results=3,
            require_human_review=False,
            enable_llm_planning=False,
            enable_llm_synthesis=False,
        )
        self.manager = ResearchRunManager(self.settings)
        await self.manager.initialize()

    async def asyncTearDown(self) -> None:
        await self.manager.shutdown()
        self.temp_dir.cleanup()

    async def test_create_run_completes_in_background(self) -> None:
        async def fake_run_research(_: dict, __: str) -> dict:
            return {
                "final_report": "# Final",
                "warnings": [],
            }

        with patch("app.run_manager.run_research", side_effect=fake_run_research):
            created = await self.manager.create_run(
                {
                    "question": "Question",
                    "output_language": "zh-CN",
                }
            )
            await self._drain_background_tasks()

        stored = self.manager.get_run(created.run_id)
        self.assertEqual(created.status, "queued")
        self.assertEqual(stored.status, "completed")
        self.assertEqual(stored.result["final_report"], "# Final")

    async def test_resume_run_requires_interrupted_status(self) -> None:
        async def fake_run_research(_: dict, __: str) -> dict:
            return {
                "draft_report": "# Draft",
                "warnings": ["Need review"],
                "__interrupt__": [{"kind": "human_review"}],
            }

        async def fake_resume_research(_: str, __: dict) -> dict:
            return {
                "final_report": "# Revised",
                "warnings": [],
            }

        with (
            patch("app.run_manager.run_research", side_effect=fake_run_research),
            patch("app.run_manager.resume_research", side_effect=fake_resume_research),
        ):
            created = await self.manager.create_run(
                {
                    "question": "Question",
                    "output_language": "zh-CN",
                }
            )
            await self._drain_background_tasks()

            interrupted = self.manager.get_run(created.run_id)
            self.assertEqual(interrupted.status, "interrupted")

            resumed = await self.manager.resume_run(
                created.run_id,
                {"approved": True, "edited_report": "# Revised"},
            )
            self.assertEqual(resumed.status, "running")

            await self._drain_background_tasks()
            completed = self.manager.get_run(created.run_id)
            self.assertEqual(completed.status, "completed")
            self.assertEqual(completed.result["final_report"], "# Revised")

        with self.assertRaises(InvalidRunStateError):
            await self.manager.resume_run(created.run_id, {"approved": True})

    async def _drain_background_tasks(self) -> None:
        while self.manager._active_tasks:
            await asyncio.gather(*list(self.manager._active_tasks.values()), return_exceptions=True)


if __name__ == "__main__":
    unittest.main()
