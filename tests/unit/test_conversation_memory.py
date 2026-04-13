from __future__ import annotations

import unittest

from app.domain.models import (
    ConversationMessage,
    ResearchConversationDetail,
    ResearchRequest,
    ResearchRunDetail,
)
from app.services.conversation_memory import (
    build_memory_context,
    rebuild_persisted_memory,
)


def _build_run(index: int) -> ResearchRunDetail:
    return ResearchRunDetail(
        run_id=f"run-{index}",
        conversation_id="conversation-1",
        origin_message_id=f"user-{index}",
        assistant_message_id=f"assistant-{index}",
        parent_run_id=f"run-{index - 1}" if index > 1 else None,
        status="completed",
        request=ResearchRequest(question=f"Question {index}", output_language="zh-CN"),
        result={
            "final_report": f"# Answer {index}\n\nDetail {index}",
            "findings": [
                {
                    "claim": f"Fact {index}",
                    "source_id": f"source-{index}",
                }
            ],
            "gaps": [f"Open question {index}"],
        },
        warnings=[],
        error_message=None,
        created_at=f"2026-04-13T00:00:0{index}+00:00",
        updated_at=f"2026-04-13T00:00:0{index}+00:00",
        completed_at=f"2026-04-13T00:00:0{index}+00:00",
    )


def _build_message(index: int, role: str, content: str) -> ConversationMessage:
    return ConversationMessage(
        message_id=f"{role}-{index}",
        conversation_id="conversation-1",
        role=role,  # type: ignore[arg-type]
        content=content,
        run_id=f"run-{index}",
        parent_message_id=f"user-{index}" if role == "assistant" else None,
        created_at=f"2026-04-13T00:00:0{index}+00:00",
        updated_at=f"2026-04-13T00:00:0{index}+00:00",
    )


class ConversationMemoryServiceTest(unittest.TestCase):
    def test_build_memory_context_keeps_recent_five_turns(self) -> None:
        runs = [_build_run(index) for index in range(1, 7)]
        messages = []
        for index in range(1, 7):
            messages.append(_build_message(index, "user", f"Question {index}"))
            messages.append(_build_message(index, "assistant", f"Answer {index}"))
        conversation = ResearchConversationDetail(
            conversation_id="conversation-1",
            title="Conversation",
            latest_message_preview="Answer 6",
            latest_run_status="completed",
            created_at="2026-04-13T00:00:01+00:00",
            updated_at="2026-04-13T00:00:06+00:00",
            messages=messages,
            runs=runs,
        )

        persisted = rebuild_persisted_memory(conversation, window_size=5)
        memory = build_memory_context(conversation, persisted, window_size=5)

        self.assertEqual(len(memory.recent_turns), 5)
        self.assertEqual(memory.recent_turns[0].run_id, "run-2")
        self.assertIn("Question 1", memory.rolling_summary)
        self.assertEqual(memory.key_facts[0].fact, "Fact 1")

    def test_build_memory_context_forces_parent_into_window(self) -> None:
        runs = [_build_run(index) for index in range(1, 8)]
        conversation = ResearchConversationDetail(
            conversation_id="conversation-1",
            title="Conversation",
            latest_message_preview="Answer 7",
            latest_run_status="completed",
            created_at="2026-04-13T00:00:01+00:00",
            updated_at="2026-04-13T00:00:07+00:00",
            messages=[],
            runs=runs,
        )

        persisted = rebuild_persisted_memory(conversation, window_size=5)
        memory = build_memory_context(conversation, persisted, window_size=5, parent_run_id="run-2")
        recent_ids = [turn.run_id for turn in memory.recent_turns]

        self.assertEqual(len(recent_ids), 5)
        self.assertIn("run-2", recent_ids)
        self.assertNotIn("Question 2", memory.rolling_summary)


if __name__ == "__main__":
    unittest.main()
