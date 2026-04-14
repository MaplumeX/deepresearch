from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.schemas import (
    ChatTurnDetailResponse,
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationMessageRequest,
    ConversationMutationResponse,
    ResearchConversationTurnRequest,
    ResumeRequest,
    RunDetailResponse,
    RunListResponse,
    RunRequest,
)
from app.chat_manager import (
    ChatConversationManager,
    ChatTurnNotFoundError,
    InvalidConversationModeError,
)
from app.run_manager import (
    InvalidRunStateError,
    ResearchRunManager,
    RunNotFoundError,
)


router = APIRouter()


def get_run_manager(request: Request) -> ResearchRunManager:
    return request.app.state.run_manager


def get_chat_manager(request: Request) -> ChatConversationManager:
    return request.app.state.chat_manager


def get_conversation_store(request: Request):
    return request.app.state.conversation_store


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/conversations", response_model=ConversationListResponse)
async def list_all_conversations(http_request: Request) -> ConversationListResponse:
    store = get_conversation_store(http_request)
    return ConversationListResponse(conversations=store.list_conversations())


@router.get("/api/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_any_conversation(conversation_id: str, http_request: Request) -> ConversationDetailResponse:
    store = get_conversation_store(http_request)
    conversation = store.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} was not found.")
    return ConversationDetailResponse(conversation=conversation)


@router.post("/api/conversations", response_model=ConversationMutationResponse)
async def create_any_conversation(
    http_request: Request,
    payload: ConversationCreateRequest,
) -> ConversationMutationResponse:
    if payload.mode == "research":
        manager = get_run_manager(http_request)
        conversation, run = await manager.create_conversation(
            ResearchConversationTurnRequest(
                question=payload.question,
                scope=payload.scope,
                output_language=payload.output_language or "zh-CN",
                max_iterations=payload.max_iterations or 2,
                max_parallel_tasks=payload.max_parallel_tasks or 3,
            ).model_dump(exclude_none=True)
        )
        return ConversationMutationResponse(conversation=conversation, run=run)

    manager = get_chat_manager(http_request)
    conversation, turn = await manager.create_conversation(
        {"question": payload.question}
    )
    return ConversationMutationResponse(conversation=conversation, turn=turn)


@router.post(
    "/api/conversations/{conversation_id}/messages",
    response_model=ConversationMutationResponse,
)
async def create_any_conversation_message(
    conversation_id: str,
    http_request: Request,
    payload: ConversationMessageRequest,
) -> ConversationMutationResponse:
    store = get_conversation_store(http_request)
    conversation = store.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} was not found.")

    if conversation.mode == "research":
        manager = get_run_manager(http_request)
        try:
            updated_conversation, run = await manager.create_message(
                conversation_id=conversation_id,
                request_payload=ResearchConversationTurnRequest(
                    question=payload.question,
                    output_language="zh-CN",
                    max_iterations=2,
                    max_parallel_tasks=3,
                    parent_run_id=payload.parent_run_id,
                ).model_dump(exclude_none=True),
            )
        except InvalidRunStateError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return ConversationMutationResponse(conversation=updated_conversation, run=run)

    manager = get_chat_manager(http_request)
    try:
        updated_conversation, turn = await manager.create_message(
            conversation_id=conversation_id,
            request_payload={"question": payload.question},
        )
    except InvalidConversationModeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ConversationMutationResponse(conversation=updated_conversation, turn=turn)


@router.post("/api/research/runs", response_model=RunDetailResponse)
async def create_run(http_request: Request, payload: RunRequest) -> RunDetailResponse:
    manager = get_run_manager(http_request)
    run = await manager.create_run(payload.model_dump(exclude_none=True))
    return RunDetailResponse(run=run)


@router.get("/api/research/runs", response_model=RunListResponse)
async def list_runs(http_request: Request) -> RunListResponse:
    manager = get_run_manager(http_request)
    return RunListResponse(runs=manager.list_runs())


@router.get("/api/research/runs/{run_id}", response_model=RunDetailResponse)
async def get_run(run_id: str, http_request: Request) -> RunDetailResponse:
    manager = get_run_manager(http_request)
    try:
        run = manager.get_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Run {run_id} was not found.") from exc
    return RunDetailResponse(run=run)


@router.get("/api/research/runs/{run_id}/events")
async def stream_run_events(run_id: str, http_request: Request) -> StreamingResponse:
    manager = get_run_manager(http_request)
    try:
        manager.get_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Run {run_id} was not found.") from exc
    event_stream = manager.stream_events(run_id)

    return StreamingResponse(
        event_stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/research/runs/{run_id}/resume", response_model=RunDetailResponse)
async def resume_run(run_id: str, http_request: Request, payload: ResumeRequest) -> RunDetailResponse:
    manager = get_run_manager(http_request)
    try:
        run = await manager.resume_run(
            run_id=run_id,
            resume_payload=payload.model_dump(exclude_none=True),
        )
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Run {run_id} was not found.") from exc
    except InvalidRunStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RunDetailResponse(run=run)


@router.get("/api/chat/turns/{turn_id}", response_model=ChatTurnDetailResponse)
async def get_chat_turn(turn_id: str, http_request: Request) -> ChatTurnDetailResponse:
    manager = get_chat_manager(http_request)
    try:
        turn = manager.get_turn(turn_id)
    except ChatTurnNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Chat turn {turn_id} was not found.") from exc
    return ChatTurnDetailResponse(turn=turn)


@router.get("/api/chat/turns/{turn_id}/events")
async def stream_chat_turn_events(turn_id: str, http_request: Request) -> StreamingResponse:
    manager = get_chat_manager(http_request)
    try:
        manager.get_turn(turn_id)
    except ChatTurnNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Chat turn {turn_id} was not found.") from exc
    event_stream = manager.stream_events(turn_id)
    return StreamingResponse(
        event_stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
