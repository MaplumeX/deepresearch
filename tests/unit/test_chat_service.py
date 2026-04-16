from __future__ import annotations

import unittest
from unittest.mock import patch

from langchain_core.messages import AIMessage, AIMessageChunk

from app.config import Settings
from app.domain.models import ConversationMessage, ResearchConversationDetail
from app.services.chat import ChatReplyResult, generate_chat_reply


class _FakeStreamingModel:
    def __init__(self) -> None:
        self.captured_messages = None

    async def astream(self, messages):
        self.captured_messages = messages
        yield AIMessageChunk(content=[], response_metadata={"id": "resp_current"}, id="resp_current")
        yield AIMessageChunk(content=[{"type": "text", "text": "Hello"}])
        yield AIMessageChunk(content=[{"type": "text", "text": " world"}], chunk_position="last")


class ChatServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            app_name="test",
            planner_model="test-model",
            synthesis_model="test-model",
            llm_api_key="dummy-key",
            llm_base_url=None,
            tavily_api_key=None,
            brave_api_key=None,
            serper_api_key=None,
            checkpoint_db_path="test.db",
            runs_db_path="test-runs.db",
            fetch_timeout_seconds=1.0,
            default_max_iterations=2,
            default_max_parallel_tasks=3,
            search_max_results=3,
            require_human_review=False,
            enable_llm_planning=False,
            enable_llm_synthesis=False,
        )

    async def test_generate_chat_reply_uses_native_text_streaming_and_preserves_response_id(self) -> None:
        model = _FakeStreamingModel()
        streamed_parts: list[tuple[str, str | None]] = []
        conversation = ResearchConversationDetail(
            conversation_id="conversation-1",
            mode="chat",
            title="Hello",
            latest_message_preview="How are you?",
            latest_run_status=None,
            created_at="2026-04-16T00:00:00+00:00",
            updated_at="2026-04-16T00:00:00+00:00",
            is_pinned=False,
            messages=[
                ConversationMessage(
                    message_id="user-1",
                    conversation_id="conversation-1",
                    role="user",
                    content="Hello",
                    created_at="2026-04-16T00:00:00+00:00",
                    updated_at="2026-04-16T00:00:00+00:00",
                ),
                ConversationMessage(
                    message_id="assistant-1",
                    conversation_id="conversation-1",
                    role="assistant",
                    content="Hi there",
                    provider_message_id="resp_previous",
                    created_at="2026-04-16T00:00:01+00:00",
                    updated_at="2026-04-16T00:00:01+00:00",
                ),
                ConversationMessage(
                    message_id="user-2",
                    conversation_id="conversation-1",
                    role="user",
                    content="How are you?",
                    created_at="2026-04-16T00:00:02+00:00",
                    updated_at="2026-04-16T00:00:02+00:00",
                ),
            ],
            runs=[],
        )

        with patch("app.services.chat.build_chat_model", return_value=model) as build_model:
            reply = await generate_chat_reply(
                self.settings,
                conversation,
                on_chunk=lambda content, provider_id: streamed_parts.append((content, provider_id)),
            )

        self.assertEqual(
            build_model.call_args.kwargs,
            {
                "temperature": 0.3,
                "use_responses_api": True,
                "use_previous_response_id": True,
            },
        )
        self.assertEqual(reply, ChatReplyResult(text="Hello world", provider_message_id="resp_current"))
        self.assertEqual(streamed_parts, [("Hello", "resp_current"), ("Hello world", "resp_current")])
        self.assertEqual(len(model.captured_messages), 4)
        self.assertIsInstance(model.captured_messages[2], AIMessage)
        self.assertEqual(model.captured_messages[2].response_metadata["id"], "resp_previous")


if __name__ == "__main__":
    unittest.main()
