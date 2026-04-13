from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.api.schemas import (
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationMutationResponse,
    ConversationTurnRequest,
    ResumeRequest,
    RunDetailResponse,
    RunListResponse,
    RunRequest,
)
from app.run_manager import (
    ConversationNotFoundError,
    InvalidRunStateError,
    ResearchRunManager,
    RunNotFoundError,
)


router = APIRouter()


def get_run_manager(request: Request) -> ResearchRunManager:
    return request.app.state.run_manager


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


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


@router.post("/api/research/conversations", response_model=ConversationMutationResponse)
async def create_conversation(
    http_request: Request,
    payload: ConversationTurnRequest,
) -> ConversationMutationResponse:
    manager = get_run_manager(http_request)
    conversation, run = await manager.create_conversation(payload.model_dump(exclude_none=True))
    return ConversationMutationResponse(conversation=conversation, run=run)


@router.get("/api/research/conversations", response_model=ConversationListResponse)
async def list_conversations(http_request: Request) -> ConversationListResponse:
    manager = get_run_manager(http_request)
    return ConversationListResponse(conversations=manager.list_conversations())


@router.get("/api/research/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(conversation_id: str, http_request: Request) -> ConversationDetailResponse:
    manager = get_run_manager(http_request)
    try:
        conversation = manager.get_conversation(conversation_id)
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} was not found.") from exc
    return ConversationDetailResponse(conversation=conversation)


@router.post(
    "/api/research/conversations/{conversation_id}/messages",
    response_model=ConversationMutationResponse,
)
async def create_conversation_message(
    conversation_id: str,
    http_request: Request,
    payload: ConversationTurnRequest,
) -> ConversationMutationResponse:
    manager = get_run_manager(http_request)
    try:
        conversation, run = await manager.create_message(
            conversation_id=conversation_id,
            request_payload=payload.model_dump(exclude_none=True),
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} was not found.") from exc
    except InvalidRunStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ConversationMutationResponse(conversation=conversation, run=run)
