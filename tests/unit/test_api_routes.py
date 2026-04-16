from __future__ import annotations

import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.run_store import ResearchRunStore


class ConversationDeleteRouteTest(unittest.TestCase):
    def setUp(self) -> None:
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
            serper_api_key=None,
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

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @contextmanager
    def _client(self):
        with patch("app.main.get_settings", return_value=self.settings), patch(
            "app.api.routes.get_settings",
            return_value=self.settings,
        ):
            with TestClient(create_app()) as client:
                yield client

    def _seed_research_conversation(
        self,
        store: ResearchRunStore,
        *,
        conversation_id: str,
        run_id: str,
        status: str,
    ) -> None:
        store.create_conversation_turn(
            conversation_id=conversation_id,
            run_id=run_id,
            request={"question": "Question", "output_language": "zh-CN"},
            origin_message_id=f"{run_id}-user",
            assistant_message_id=f"{run_id}-assistant",
            title="Question",
        )
        if status == "running":
            store.set_status(run_id, "running")
        elif status == "completed":
            store.store_result(run_id, "completed", {"final_report": "# Final", "warnings": []})

    def _seed_chat_conversation(
        self,
        store: ResearchRunStore,
        *,
        conversation_id: str,
        turn_id: str,
        status: str,
    ) -> None:
        store.create_chat_turn(
            conversation_id=conversation_id,
            turn_id=turn_id,
            request={"question": "Hello"},
            origin_message_id=f"{turn_id}-user",
            assistant_message_id=f"{turn_id}-assistant",
            title="Hello",
        )
        if status == "running":
            store.set_chat_turn_status(turn_id, "running")
        elif status == "completed":
            store.store_chat_turn_result(turn_id, "Hello back")

    def test_delete_conversation_rejects_active_research_run(self) -> None:
        with self._client() as client:
            store = client.app.state.conversation_store
            conversation_id = "conversation-research-active"
            self._seed_research_conversation(
                store,
                conversation_id=conversation_id,
                run_id="run-active",
                status="queued",
            )

            response = client.delete(f"/api/conversations/{conversation_id}")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"],
            f"Conversation {conversation_id} has active runs or chat turns and cannot be deleted.",
        )
        self.assertIsNotNone(store.get_conversation(conversation_id))

    def test_delete_conversation_rejects_active_chat_turn(self) -> None:
        with self._client() as client:
            store = client.app.state.conversation_store
            conversation_id = "conversation-chat-active"
            self._seed_chat_conversation(
                store,
                conversation_id=conversation_id,
                turn_id="turn-active",
                status="running",
            )

            response = client.delete(f"/api/conversations/{conversation_id}")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"],
            f"Conversation {conversation_id} has active runs or chat turns and cannot be deleted.",
        )
        self.assertIsNotNone(store.get_conversation(conversation_id))

    def test_delete_conversation_removes_idle_conversation(self) -> None:
        with self._client() as client:
            store = client.app.state.conversation_store
            conversation_id = "conversation-idle"
            self._seed_research_conversation(
                store,
                conversation_id=conversation_id,
                run_id="run-completed",
                status="completed",
            )

            response = client.delete(f"/api/conversations/{conversation_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertIsNone(store.get_conversation(conversation_id))


class ConversationCreateRouteTest(unittest.TestCase):
    def setUp(self) -> None:
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
            serper_api_key=None,
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

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @contextmanager
    def _client(self):
        with patch("app.main.get_settings", return_value=self.settings), patch(
            "app.api.routes.get_settings",
            return_value=self.settings,
        ):
            with TestClient(create_app()) as client:
                yield client

    def test_create_research_conversation_returns_503_when_llm_is_not_ready(self) -> None:
        with self._client() as client:
            response = client.post(
                "/api/conversations",
                json={"mode": "research", "question": "Question", "output_language": "zh-CN"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("Research mode requires a configured LLM", response.json()["detail"])

    def test_create_chat_conversation_returns_503_when_llm_is_not_ready(self) -> None:
        with self._client() as client:
            response = client.post(
                "/api/conversations",
                json={"mode": "chat", "question": "Hello"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("Chat mode requires a configured LLM", response.json()["detail"])

    def test_create_run_returns_503_when_llm_is_not_ready(self) -> None:
        with self._client() as client:
            response = client.post(
                "/api/research/runs",
                json={"question": "Question", "output_language": "zh-CN"},
            )

        self.assertEqual(response.status_code, 503)
        self.assertIn("Research mode requires a configured LLM", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
