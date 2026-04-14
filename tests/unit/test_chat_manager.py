from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.chat_manager import ChatConversationManager, InvalidConversationModeError
from app.config import Settings
from app.run_manager import ResearchRunManager


class ChatConversationManagerTest(unittest.IsolatedAsyncioTestCase):
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
        self.manager = ChatConversationManager(self.settings)
        self.research_manager = ResearchRunManager(self.settings)
        await self.manager.initialize()
        await self.research_manager.initialize()

    async def asyncTearDown(self) -> None:
        await self.manager.shutdown()
        await self.research_manager.shutdown()
        self.temp_dir.cleanup()

    async def test_create_conversation_completes_in_background(self) -> None:
        async def fake_generate_reply(_, __):
            return "Hello back"

        with patch("app.chat_manager.generate_chat_reply", side_effect=fake_generate_reply):
            conversation, turn = await self.manager.create_conversation({"question": "Hello"})
            await self._drain_background_tasks()

        refreshed = self.manager._store.get_conversation(conversation.conversation_id)
        stored_turn = self.manager.get_turn(turn.turn_id)

        self.assertIsNotNone(refreshed)
        self.assertEqual(refreshed.mode, "chat")
        self.assertEqual(stored_turn.status, "completed")
        self.assertEqual(refreshed.messages[-1].content, "Hello back")

    async def test_create_message_rejects_research_conversation(self) -> None:
        async def fake_run_research(_, __, ___):
            return {"final_report": "# Final", "warnings": []}

        with patch("app.run_manager.run_research", side_effect=fake_run_research):
            research_conversation, _ = await self.research_manager.create_conversation(
                {
                    "question": "Question",
                    "output_language": "zh-CN",
                }
            )
            await self._drain_research_background_tasks()

        with self.assertRaises(InvalidConversationModeError):
            await self.manager.create_message(research_conversation.conversation_id, {"question": "Hi"})

    async def _drain_background_tasks(self) -> None:
        while self.manager._active_tasks:
            await asyncio.gather(*list(self.manager._active_tasks.values()), return_exceptions=True)

    async def _drain_research_background_tasks(self) -> None:
        while self.research_manager._active_tasks:
            await asyncio.gather(*list(self.research_manager._active_tasks.values()), return_exceptions=True)


if __name__ == "__main__":
    unittest.main()
