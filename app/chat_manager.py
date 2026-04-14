from __future__ import annotations

import asyncio
from collections import defaultdict
from contextlib import suppress
from datetime import datetime, timezone
from uuid import uuid4

from app.config import Settings
from app.domain.models import (
    ChatEventType,
    ChatTurnDetail,
    ChatTurnEvent,
    ChatTurnStatus,
    ResearchConversationDetail,
)
from app.run_store import ResearchRunStore, build_conversation_title
from app.services.chat import generate_chat_reply


TERMINAL_CHAT_STATUSES = {"completed", "failed"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChatTurnNotFoundError(Exception):
    pass


class ChatConversationNotFoundError(Exception):
    pass


class InvalidConversationModeError(Exception):
    pass


class ChatEventBroker:
    def __init__(self) -> None:
        self._queues: dict[str, set[asyncio.Queue[ChatTurnEvent]]] = defaultdict(set)

    def subscribe(self, turn_id: str) -> asyncio.Queue[ChatTurnEvent]:
        queue: asyncio.Queue[ChatTurnEvent] = asyncio.Queue()
        self._queues[turn_id].add(queue)
        return queue

    def unsubscribe(self, turn_id: str, queue: asyncio.Queue[ChatTurnEvent]) -> None:
        subscribers = self._queues.get(turn_id)
        if subscribers is None:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._queues.pop(turn_id, None)

    def publish(self, event: ChatTurnEvent) -> None:
        for queue in list(self._queues.get(event.turn_id, set())):
            queue.put_nowait(event)


class ChatConversationManager:
    def __init__(self, settings: Settings, store: ResearchRunStore | None = None) -> None:
        self._settings = settings
        self._store = store or ResearchRunStore(settings.runs_db_path)
        self._broker = ChatEventBroker()
        self._active_tasks: dict[str, asyncio.Task[None]] = {}

    async def initialize(self) -> None:
        self._store.initialize()
        self._store.fail_incomplete_chat_turns("Server restarted before the chat reply completed.")

    async def shutdown(self) -> None:
        tasks = list(self._active_tasks.values())
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task

    async def create_conversation(
        self,
        request_payload: dict,
    ) -> tuple[ResearchConversationDetail, ChatTurnDetail]:
        return self._create_turn(
            conversation_id=uuid4().hex,
            request_payload=request_payload,
            title=build_conversation_title(str(request_payload.get("question", ""))),
        )

    async def create_message(
        self,
        conversation_id: str,
        request_payload: dict,
    ) -> tuple[ResearchConversationDetail, ChatTurnDetail]:
        conversation = self._store.get_conversation(conversation_id)
        if conversation is None:
            raise ChatConversationNotFoundError(conversation_id)
        if conversation.mode != "chat":
            raise InvalidConversationModeError(
                f"Conversation {conversation_id} is in mode {conversation.mode}, expected chat.",
            )
        return self._create_turn(conversation_id=conversation_id, request_payload=request_payload, title=None)

    def get_turn(self, turn_id: str) -> ChatTurnDetail:
        turn = self._store.get_chat_turn(turn_id)
        if turn is None:
            raise ChatTurnNotFoundError(turn_id)
        return turn

    async def stream_events(self, turn_id: str):
        turn = self.get_turn(turn_id)
        initial_event = self._build_event(self._event_type_for_status(turn.status), turn, {})
        yield self._format_sse(initial_event)

        if turn.status in TERMINAL_CHAT_STATUSES:
            return

        queue = self._broker.subscribe(turn_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue

                yield self._format_sse(event)
                if event.status in TERMINAL_CHAT_STATUSES:
                    return
        finally:
            self._broker.unsubscribe(turn_id, queue)

    def _create_turn(
        self,
        *,
        conversation_id: str,
        request_payload: dict,
        title: str | None,
    ) -> tuple[ResearchConversationDetail, ChatTurnDetail]:
        turn_id = uuid4().hex
        origin_message_id = uuid4().hex
        assistant_message_id = uuid4().hex
        conversation, turn = self._store.create_chat_turn(
            conversation_id=conversation_id,
            turn_id=turn_id,
            request=request_payload,
            origin_message_id=origin_message_id,
            assistant_message_id=assistant_message_id,
            title=title,
        )
        self._publish("chat.turn.created", turn, {})
        self._start_background_task(turn_id, self._execute_turn(turn_id))
        return conversation, turn

    def _start_background_task(self, turn_id: str, coroutine) -> None:
        task = asyncio.create_task(coroutine)
        self._active_tasks[turn_id] = task

        def _cleanup(done_task: asyncio.Task[None]) -> None:
            current = self._active_tasks.get(turn_id)
            if current is done_task:
                self._active_tasks.pop(turn_id, None)

        task.add_done_callback(_cleanup)

    async def _execute_turn(self, turn_id: str) -> None:
        running_turn = self._store.set_chat_turn_status(turn_id, "running")
        self._publish("chat.turn.status_changed", running_turn, {"message": "Chat reply started."})

        try:
            conversation = self._store.get_conversation(running_turn.conversation_id, expected_mode="chat")
            if conversation is None:
                raise ChatConversationNotFoundError(running_turn.conversation_id)
            reply = await generate_chat_reply(self._settings, conversation)
        except asyncio.CancelledError:
            failed_turn = self._store.mark_chat_turn_failed(turn_id, "Reply was cancelled during shutdown.")
            self._publish("chat.turn.failed", failed_turn, {})
            raise
        except Exception as exc:
            failed_turn = self._store.mark_chat_turn_failed(turn_id, str(exc))
            self._publish("chat.turn.failed", failed_turn, {})
            return

        completed_turn = self._store.store_chat_turn_result(turn_id, reply)
        self._publish("chat.turn.completed", completed_turn, {})

    def _publish(self, event_type: ChatEventType, turn: ChatTurnDetail, data: dict) -> None:
        self._broker.publish(self._build_event(event_type, turn, data))

    def _build_event(self, event_type: ChatEventType, turn: ChatTurnDetail, data: dict) -> ChatTurnEvent:
        payload = {
            "turn": turn.model_dump(),
        }
        conversation = self._store.get_conversation_summary(turn.conversation_id)
        if conversation is not None:
            payload["conversation"] = conversation.model_dump()
        assistant_message = self._store.get_message(turn.assistant_message_id)
        if assistant_message is not None:
            payload["assistant_message"] = assistant_message.model_dump()
        payload.update(data)
        return ChatTurnEvent(
            type=event_type,
            turn_id=turn.turn_id,
            status=turn.status,
            timestamp=utc_now_iso(),
            data=payload,
        )

    def _event_type_for_status(self, status: ChatTurnStatus) -> ChatEventType:
        if status == "completed":
            return "chat.turn.completed"
        if status == "failed":
            return "chat.turn.failed"
        return "chat.turn.status_changed"

    def _format_sse(self, event: ChatTurnEvent) -> str:
        return (
            f"event: {event.type}\n"
            f"data: {event.model_dump_json()}\n\n"
        )
