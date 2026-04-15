from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.domain.models import MemoryFact, PersistedConversationMemory, ResearchRunEvent
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
        self.assertEqual(conversation.mode, "research")
        self.assertEqual(len(conversation.messages), 2)
        self.assertEqual(conversation.messages[0].role, "user")
        self.assertEqual(conversation.messages[1].role, "assistant")

    def test_create_chat_turn_persists_chat_mode_without_research_runs(self) -> None:
        conversation, turn = self.store.create_chat_turn(
            conversation_id="chat-1",
            turn_id="turn-1",
            request={"question": "Hello"},
            origin_message_id="message-1",
            assistant_message_id="message-2",
            title="Hello",
        )

        stored_turn = self.store.get_chat_turn(turn.turn_id)
        listed_chat = self.store.list_conversations(mode="chat")
        listed_research = self.store.list_conversations(mode="research")

        self.assertEqual(conversation.mode, "chat")
        self.assertIsNotNone(stored_turn)
        self.assertEqual(stored_turn.status, "queued")
        self.assertEqual(len(conversation.runs), 0)
        self.assertEqual(len(conversation.messages), 2)
        self.assertEqual(len(listed_chat), 1)
        self.assertEqual(len(listed_research), 0)

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

    def test_append_run_event_persists_history_for_detail_and_conversation(self) -> None:
        created = self.store.create_run(
            "run-events",
            {
                "question": "Question",
                "output_language": "zh-CN",
            },
        )

        self.store.append_run_event(
            "run-events",
            ResearchRunEvent(
                type="run.progress",
                run_id="run-events",
                status="running",
                timestamp="2026-04-15T00:00:00+00:00",
                data={
                    "message": "Planning research tasks.",
                    "progress": {
                        "phase": "planning",
                        "phase_label": "Planning research",
                        "iteration": 1,
                        "max_iterations": 2,
                        "task": None,
                        "counts": {
                            "planned_tasks": 3,
                            "completed_tasks": 0,
                            "search_hits": None,
                            "acquired_contents": None,
                            "kept_sources": None,
                            "evidence_count": None,
                            "warnings": 0,
                        },
                        "review": {
                            "required": False,
                            "kind": None,
                        },
                    },
                },
            ),
        )

        run = self.store.get_run("run-events")
        conversation = self.store.get_conversation(created.conversation_id)

        self.assertIsNotNone(run)
        self.assertEqual(len(run.progress_events), 1)
        self.assertEqual(run.progress_events[0].message, "Planning research tasks.")
        self.assertIsNotNone(conversation)
        self.assertEqual(conversation.runs[0].progress_events[0].progress.phase, "planning")

    def test_upsert_and_get_conversation_memory(self) -> None:
        self.store.upsert_conversation_memory(
            PersistedConversationMemory(
                conversation_id="conversation-1",
                rolling_summary="- Q: Earlier question | A: Earlier answer",
                key_facts=[MemoryFact(fact="Fact 1", source_ids=["source-1"])],
                open_questions=["Need more corroboration"],
                updated_at="2026-04-13T00:00:00+00:00",
            )
        )

        stored = self.store.get_conversation_memory("conversation-1")

        self.assertIsNotNone(stored)
        self.assertEqual(stored.rolling_summary, "- Q: Earlier question | A: Earlier answer")
        self.assertEqual(stored.key_facts[0].fact, "Fact 1")
        self.assertEqual(stored.open_questions, ["Need more corroboration"])


if __name__ == "__main__":
    unittest.main()
