from __future__ import annotations

import asyncio
from collections import defaultdict
from contextlib import suppress
from datetime import datetime, timezone
from uuid import uuid4

from app.config import Settings
from app.domain.models import (
    ResearchProgressPayload,
    ResearchConversationDetail,
    ResearchConversationSummary,
    ResearchRunDetail,
    ResearchRunEvent,
    ResearchRunHistoryEvent,
    ResearchRunSummary,
    RunEventType,
    RunStatus,
)
from app.run_store import ResearchRunStore, build_conversation_title
from app.runtime import resume_research, run_research
from app.services.research_progress import build_counts, build_progress_payload
from app.services.conversation_memory import (
    DEFAULT_MEMORY_WINDOW,
    build_memory_context,
    empty_memory_payload,
    rebuild_persisted_memory,
)


TERMINAL_RUN_STATUSES = {"completed", "failed", "interrupted"}
ACTIVE_RUN_STATUSES = {"queued", "running"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunNotFoundError(Exception):
    pass


class ConversationNotFoundError(Exception):
    pass


class InvalidRunStateError(Exception):
    pass


class RunEventBroker:
    def __init__(self) -> None:
        self._queues: dict[str, set[asyncio.Queue[ResearchRunEvent]]] = defaultdict(set)

    def subscribe(self, run_id: str) -> asyncio.Queue[ResearchRunEvent]:
        queue: asyncio.Queue[ResearchRunEvent] = asyncio.Queue()
        self._queues[run_id].add(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue[ResearchRunEvent]) -> None:
        subscribers = self._queues.get(run_id)
        if subscribers is None:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._queues.pop(run_id, None)

    def publish(self, event: ResearchRunEvent) -> None:
        for queue in list(self._queues.get(event.run_id, set())):
            queue.put_nowait(event)


class ResearchRunManager:
    def __init__(self, settings: Settings, store: ResearchRunStore | None = None) -> None:
        self._settings = settings
        self._store = store or ResearchRunStore(settings.runs_db_path)
        self._broker = RunEventBroker()
        self._active_tasks: dict[str, asyncio.Task[None]] = {}

    async def initialize(self) -> None:
        self._store.initialize()
        self._store.fail_incomplete_runs("Server restarted before the run completed.")

    async def shutdown(self) -> None:
        tasks = list(self._active_tasks.values())
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task

    async def create_run(self, request_payload: dict) -> ResearchRunDetail:
        _, run = self._create_turn_in_new_conversation(request_payload)
        return run

    async def create_conversation(self, request_payload: dict) -> tuple[ResearchConversationDetail, ResearchRunDetail]:
        return self._create_turn_in_new_conversation(request_payload)

    async def create_message(
        self,
        conversation_id: str,
        request_payload: dict,
    ) -> tuple[ResearchConversationDetail, ResearchRunDetail]:
        conversation = self.get_conversation(conversation_id)
        persisted_memory = self._store.get_conversation_memory(conversation_id)
        payload = dict(request_payload)
        parent_run_id = payload.pop("parent_run_id", None)
        resolved_parent_run_id = self._resolve_parent_run_id(conversation, parent_run_id)
        memory_context = build_memory_context(
            conversation,
            persisted_memory,
            window_size=DEFAULT_MEMORY_WINDOW,
            parent_run_id=resolved_parent_run_id,
        )
        return self._create_turn(
            conversation_id=conversation_id,
            request_payload=payload,
            title=None,
            parent_run_id=resolved_parent_run_id,
            memory_context=memory_context.model_dump(),
        )

    def list_runs(self) -> list[ResearchRunSummary]:
        return self._store.list_runs()

    def list_conversations(self) -> list[ResearchConversationSummary]:
        return self._store.list_conversations(mode="research")

    def get_run(self, run_id: str) -> ResearchRunDetail:
        run = self._store.get_run(run_id)
        if run is None:
            raise RunNotFoundError(run_id)
        return run

    def get_conversation(self, conversation_id: str) -> ResearchConversationDetail:
        conversation = self._store.get_conversation(conversation_id, expected_mode="research")
        if conversation is None:
            raise ConversationNotFoundError(conversation_id)
        return conversation

    async def resume_run(self, run_id: str, resume_payload: dict) -> ResearchRunDetail:
        run = self.get_run(run_id)
        if run.status != "interrupted":
            raise InvalidRunStateError(f"Run {run_id} is in status {run.status}, not interrupted.")
        if run_id in self._active_tasks and not self._active_tasks[run_id].done():
            raise InvalidRunStateError(f"Run {run_id} is already active.")

        updated_run = self._store.set_status(run_id, "running")
        self._publish(
            "run.resumed",
            updated_run,
            {
                "message": "Review submitted. Resuming research.",
                "resume_payload": resume_payload,
                "progress": self._build_progress_snapshot(updated_run, "finalizing").model_dump(),
            },
        )
        self._start_background_task(run_id, self._execute_resume(run_id, resume_payload))
        return updated_run

    async def stream_events(self, run_id: str):
        run = self.get_run(run_id)
        latest_event = self._store.get_latest_run_event(run_id)
        if latest_event is not None:
            initial_event = self._build_event_from_history(run, latest_event)
        else:
            initial_event = self._build_event(self._event_type_for_status(run.status), run, {})
        yield self._format_sse(initial_event)

        if run.status in TERMINAL_RUN_STATUSES:
            return

        queue = self._broker.subscribe(run_id)
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue

                yield self._format_sse(event)
                if event.status in TERMINAL_RUN_STATUSES:
                    return
        finally:
            self._broker.unsubscribe(run_id, queue)

    def _create_turn_in_new_conversation(
        self,
        request_payload: dict,
    ) -> tuple[ResearchConversationDetail, ResearchRunDetail]:
        title = build_conversation_title(str(request_payload.get("question", "")))
        return self._create_turn(
            conversation_id=uuid4().hex,
            request_payload=request_payload,
            title=title,
            parent_run_id=None,
            memory_context=empty_memory_payload().model_dump(),
        )

    def _create_turn(
        self,
        *,
        conversation_id: str,
        request_payload: dict,
        title: str | None,
        parent_run_id: str | None,
        memory_context: dict | None,
    ) -> tuple[ResearchConversationDetail, ResearchRunDetail]:
        run_id = uuid4().hex
        origin_message_id = uuid4().hex
        assistant_message_id = uuid4().hex
        conversation, run = self._store.create_conversation_turn(
            conversation_id=conversation_id,
            run_id=run_id,
            request=request_payload,
            origin_message_id=origin_message_id,
            assistant_message_id=assistant_message_id,
            title=title,
            parent_run_id=parent_run_id,
        )
        self._publish(
            "run.created",
            run,
            {
                "message": "Research run queued.",
                "progress": build_progress_payload(
                    "queued",
                    max_iterations=run.request.max_iterations,
                ).model_dump(),
            },
        )
        self._start_background_task(run_id, self._execute_run(run_id, request_payload, memory_context))
        return conversation, run

    def _resolve_parent_run_id(
        self,
        conversation: ResearchConversationDetail,
        parent_run_id: str | None,
    ) -> str | None:
        candidate = parent_run_id
        if candidate is None and conversation.runs:
            candidate = conversation.runs[-1].run_id
        if candidate is None:
            return None

        parent_run = self.get_run(candidate)
        if parent_run.conversation_id != conversation.conversation_id:
            raise InvalidRunStateError(
                f"Run {candidate} does not belong to conversation {conversation.conversation_id}.",
            )
        if parent_run.status in ACTIVE_RUN_STATUSES:
            raise InvalidRunStateError(f"Run {candidate} is still active and cannot accept follow-up turns yet.")
        return candidate

    def _start_background_task(self, run_id: str, coroutine) -> None:
        task = asyncio.create_task(coroutine)
        self._active_tasks[run_id] = task

        def _cleanup(done_task: asyncio.Task[None]) -> None:
            current = self._active_tasks.get(run_id)
            if current is done_task:
                self._active_tasks.pop(run_id, None)

        task.add_done_callback(_cleanup)

    async def _execute_run(
        self,
        run_id: str,
        request_payload: dict,
        memory_context: dict | None,
    ) -> None:
        running_run = self._store.set_status(run_id, "running")
        self._publish(
            "run.status_changed",
            running_run,
            {
                "message": "Research execution started.",
                "progress": build_progress_payload(
                    "clarifying_scope",
                    max_iterations=running_run.request.max_iterations,
                ).model_dump(),
            },
        )
        await self._finish_execution(
            run_id,
            self._run_research_with_progress(run_id, request_payload, memory_context),
        )

    async def _execute_resume(self, run_id: str, resume_payload: dict) -> None:
        await self._finish_execution(
            run_id,
            self._resume_research_with_progress(run_id, resume_payload),
        )

    async def _finish_execution(self, run_id: str, execution) -> None:
        try:
            result = await execution
        except asyncio.CancelledError:
            failed_run = self._store.mark_failed(run_id, "Run was cancelled during shutdown.")
            self._refresh_conversation_memory(failed_run.conversation_id)
            self._publish(
                "run.failed",
                failed_run,
                {
                    "message": failed_run.error_message,
                    "progress": self._build_progress_snapshot(failed_run, "failed").model_dump(),
                },
            )
            raise
        except Exception as exc:
            failed_run = self._store.mark_failed(run_id, str(exc))
            self._refresh_conversation_memory(failed_run.conversation_id)
            self._publish(
                "run.failed",
                failed_run,
                {
                    "message": str(exc),
                    "progress": self._build_progress_snapshot(failed_run, "failed").model_dump(),
                },
            )
            return

        status: RunStatus = "interrupted" if "__interrupt__" in result else "completed"
        updated_run = self._store.store_result(run_id, status, result)
        self._refresh_conversation_memory(updated_run.conversation_id)
        event_type = "run.interrupted" if status == "interrupted" else "run.completed"
        terminal_phase = "awaiting_review" if status == "interrupted" else "completed"
        self._publish(
            event_type,
            updated_run,
            {
                "message": "Research paused for review." if status == "interrupted" else "Research completed.",
                "progress": self._build_progress_snapshot(
                    updated_run,
                    terminal_phase,
                    review_required=status == "interrupted",
                    review_kind="human_review" if status == "interrupted" else None,
                ).model_dump(),
            },
        )

    def _refresh_conversation_memory(self, conversation_id: str) -> None:
        conversation = self._store.get_conversation(conversation_id)
        if conversation is None:
            return
        memory = rebuild_persisted_memory(conversation, window_size=DEFAULT_MEMORY_WINDOW)
        self._store.upsert_conversation_memory(memory)

    def _publish(self, event_type: RunEventType, run: ResearchRunDetail, data: dict) -> None:
        event = self._build_event(event_type, run, data)
        self._store.append_run_event(run.run_id, event)
        self._broker.publish(event)

    def _build_event(
        self,
        event_type: RunEventType,
        run: ResearchRunDetail,
        data: dict,
        *,
        timestamp: str | None = None,
    ) -> ResearchRunEvent:
        payload = {
            "run": run.model_dump(exclude={"progress_events"}),
        }
        conversation = self._store.get_conversation_summary(run.conversation_id)
        if conversation is not None:
            payload["conversation"] = conversation.model_dump()
        assistant_message = self._store.get_message(run.assistant_message_id)
        if assistant_message is not None:
            payload["assistant_message"] = assistant_message.model_dump()
        payload.update(data)
        return ResearchRunEvent(
            type=event_type,
            run_id=run.run_id,
            status=run.status,
            timestamp=timestamp or utc_now_iso(),
            data=payload,
        )

    def _build_event_from_history(
        self,
        run: ResearchRunDetail,
        history_event: ResearchRunHistoryEvent,
    ) -> ResearchRunEvent:
        data: dict = {}
        if history_event.message is not None:
            data["message"] = history_event.message
        if history_event.progress is not None:
            data["progress"] = history_event.progress.model_dump()
        return self._build_event(
            history_event.event_type,
            run,
            data,
            timestamp=history_event.timestamp,
        )

    def _event_type_for_status(self, status: RunStatus) -> RunEventType:
        if status == "completed":
            return "run.completed"
        if status == "failed":
            return "run.failed"
        if status == "interrupted":
            return "run.interrupted"
        return "run.status_changed"

    def _format_sse(self, event: ResearchRunEvent) -> str:
        return (
            f"event: {event.type}\n"
            f"data: {event.model_dump_json()}\n\n"
        )

    def _make_progress_listener(self, run_id: str):
        def listener(payload: dict) -> None:
            run = self.get_run(run_id)
            data = dict(payload)
            progress = data.get("progress")
            if isinstance(progress, ResearchProgressPayload):
                data["progress"] = progress.model_dump()
            self._publish("run.progress", run, data)

        return listener

    def _build_progress_snapshot(
        self,
        run: ResearchRunDetail,
        phase: str,
        *,
        review_required: bool = False,
        review_kind: str | None = None,
    ) -> ResearchProgressPayload:
        result = run.result if isinstance(run.result, dict) else {}
        return build_progress_payload(
            phase,
            iteration=result.get("iteration_count") if isinstance(result.get("iteration_count"), int) else None,
            max_iterations=run.request.max_iterations,
            counts=build_counts(
                planned_tasks=self._safe_size(result.get("tasks")),
                completed_tasks=self._safe_size(result.get("task_outcomes")),
                kept_sources=self._safe_size(result.get("sources")),
                evidence_count=self._safe_size(result.get("findings")),
                warnings=len(run.warnings) or None,
            ),
            review_required=review_required,
            review_kind=review_kind,
        )

    def _safe_size(self, value) -> int | None:
        if isinstance(value, (list, tuple, set, dict)):
            return len(value)
        return None

    async def _run_research_with_progress(
        self,
        run_id: str,
        request_payload: dict,
        memory_context: dict | None,
    ) -> dict:
        listener = self._make_progress_listener(run_id)
        try:
            return await run_research(
                request_payload,
                run_id,
                memory_context,
                on_progress=listener,
            )
        except TypeError as exc:
            if "on_progress" not in str(exc):
                raise
            return await run_research(request_payload, run_id, memory_context)

    async def _resume_research_with_progress(self, run_id: str, resume_payload: dict) -> dict:
        listener = self._make_progress_listener(run_id)
        try:
            return await resume_research(
                run_id,
                resume_payload,
                on_progress=listener,
            )
        except TypeError as exc:
            if "on_progress" not in str(exc):
                raise
            return await resume_research(run_id, resume_payload)
