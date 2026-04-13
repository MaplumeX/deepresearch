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

    def test_create_run_also_creates_conversation_thread(self) -> None:
        created = self.store.create_run(
            "run-1",
            {
                "question": "How do I build a deep research agent?",
                "output_language": "zh-CN",
            },
        )

        listed_runs = self.store.list_runs()
        listed_conversations = self.store.list_conversations()
        conversation = self.store.get_conversation(created.conversation_id)

        self.assertEqual(created.status, "queued")
        self.assertEqual(created.conversation_id, "run-1")
        self.assertEqual(len(listed_runs), 1)
        self.assertEqual(len(listed_conversations), 1)
        self.assertIsNotNone(conversation)
        self.assertEqual(len(conversation.messages), 2)
        self.assertEqual(conversation.messages[0].role, "user")
        self.assertEqual(conversation.messages[1].role, "assistant")

    def test_create_follow_up_turn_links_to_parent_run(self) -> None:
        initial = self.store.create_run(
            "run-1",
            {
                "question": "Question",
                "output_language": "zh-CN",
            },
        )
        self.store.store_result(
            "run-1",
            "completed",
            {
                "final_report": "# Final",
                "warnings": [],
            },
        )

        _, follow_up = self.store.create_conversation_turn(
            conversation_id=initial.conversation_id,
            run_id="run-2",
            request={
                "question": "Follow-up",
                "output_language": "zh-CN",
            },
            origin_message_id="message-3",
            assistant_message_id="message-4",
            parent_run_id="run-1",
        )

        conversation = self.store.get_conversation(initial.conversation_id)

        self.assertEqual(follow_up.parent_run_id, "run-1")
        self.assertIsNotNone(conversation)
        self.assertEqual(len(conversation.messages), 4)
        self.assertEqual(conversation.messages[2].parent_message_id, initial.assistant_message_id)

    def test_store_result_extracts_warnings_and_updates_assistant_message(self) -> None:
        created = self.store.create_run(
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
        assistant_message = self.store.get_message(created.assistant_message_id)

        self.assertEqual(updated.status, "interrupted")
        self.assertEqual(updated.warnings, ["Need manual review"])
        self.assertEqual(updated.result["draft_report"], "# Draft")
        self.assertIsNotNone(assistant_message)
        self.assertEqual(assistant_message.content, "# Draft")


if __name__ == "__main__":
    unittest.main()
