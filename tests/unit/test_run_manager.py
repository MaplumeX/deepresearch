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
            brave_api_key=None,
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

    async def test_create_run_completes_in_background_and_populates_conversation(self) -> None:
        async def fake_run_research(_: dict, __: str, ___: dict | None) -> dict:
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
        conversation = self.manager.get_conversation(created.conversation_id)
        self.assertEqual(created.status, "queued")
        self.assertEqual(stored.status, "completed")
        self.assertEqual(stored.result["final_report"], "# Final")
        self.assertEqual(stored.progress_events[0].progress.phase, "queued")
        self.assertEqual(stored.progress_events[-1].progress.phase, "completed")
        self.assertEqual(len(conversation.messages), 2)
        self.assertEqual(conversation.messages[-1].content, "# Final")

    async def test_create_message_adds_follow_up_turn_in_same_conversation(self) -> None:
        captured_memories: list[dict | None] = []

        async def fake_run_research(request_payload: dict, _: str, memory: dict | None) -> dict:
            captured_memories.append(memory)
            return {
                "final_report": f"# {request_payload['question']}",
                "warnings": [],
            }

        with patch("app.run_manager.run_research", side_effect=fake_run_research):
            conversation, first_run = await self.manager.create_conversation(
                {
                    "question": "Question",
                    "output_language": "zh-CN",
                }
            )
            await self._drain_background_tasks()

            next_conversation, second_run = await self.manager.create_message(
                conversation.conversation_id,
                {
                    "question": "Follow-up",
                    "output_language": "zh-CN",
                },
            )
            await self._drain_background_tasks()

        refreshed = self.manager.get_conversation(conversation.conversation_id)
        self.assertEqual(next_conversation.conversation_id, conversation.conversation_id)
        self.assertEqual(second_run.parent_run_id, first_run.run_id)
        self.assertEqual(len(refreshed.runs), 2)
        self.assertEqual(len(refreshed.messages), 4)
        self.assertEqual(refreshed.messages[-1].content, "# Follow-up")
        self.assertEqual(captured_memories[0]["recent_turns"], [])
        self.assertEqual(len(captured_memories[1]["recent_turns"]), 1)
        self.assertEqual(captured_memories[1]["recent_turns"][0]["question"], "Question")

    async def test_resume_run_requires_interrupted_status(self) -> None:
        async def fake_run_research(_: dict, __: str, ___: dict | None) -> dict:
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
            conversation = self.manager.get_conversation(created.conversation_id)
            self.assertEqual(completed.status, "completed")
            self.assertEqual(completed.result["final_report"], "# Revised")
            self.assertEqual(conversation.messages[-1].content, "# Revised")

        with self.assertRaises(InvalidRunStateError):
            await self.manager.resume_run(created.run_id, {"approved": True})

    async def test_create_message_rejects_active_parent_run(self) -> None:
        blocker = asyncio.Event()

        async def blocking_run_research(_: dict, __: str, ___: dict | None) -> dict:
            await blocker.wait()
            return {
                "final_report": "# Final",
                "warnings": [],
            }

        with patch("app.run_manager.run_research", side_effect=blocking_run_research):
            conversation, _ = await self.manager.create_conversation(
                {
                    "question": "Question",
                    "output_language": "zh-CN",
                }
            )

            with self.assertRaises(InvalidRunStateError):
                await self.manager.create_message(
                    conversation.conversation_id,
                    {
                        "question": "Follow-up",
                        "output_language": "zh-CN",
                    },
                )

            blocker.set()
            await self._drain_background_tasks()

    async def _drain_background_tasks(self) -> None:
        while self.manager._active_tasks:
            await asyncio.gather(*list(self.manager._active_tasks.values()), return_exceptions=True)


if __name__ == "__main__":
    unittest.main()
