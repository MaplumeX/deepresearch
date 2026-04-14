from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.models import (
    ConversationMode,
    ChatTurnDetail,
    ResearchConversationDetail,
    ResearchConversationSummary,
    ResearchRequest,
    ResearchRunDetail,
    ResearchRunSummary,
)


class RunRequest(ResearchRequest):
    pass


class ResumeRequest(BaseModel):
    approved: bool = True
    edited_report: str | None = None


class ResearchConversationTurnRequest(ResearchRequest):
    parent_run_id: str | None = None


class ConversationCreateRequest(BaseModel):
    mode: ConversationMode
    question: str = Field(min_length=1)
    scope: str | None = None
    output_language: Literal["zh-CN", "en"] | None = None
    max_iterations: int | None = Field(default=None, ge=1, le=5)
    max_parallel_tasks: int | None = Field(default=None, ge=1, le=5)


class ConversationMessageRequest(BaseModel):
    question: str = Field(min_length=1)
    parent_run_id: str | None = None


class RunDetailResponse(BaseModel):
    run: ResearchRunDetail


class RunListResponse(BaseModel):
    runs: list[ResearchRunSummary]


class ConversationDetailResponse(BaseModel):
    conversation: ResearchConversationDetail


class ConversationListResponse(BaseModel):
    conversations: list[ResearchConversationSummary]


class ConversationMutationResponse(BaseModel):
    conversation: ResearchConversationDetail
    run: ResearchRunDetail | None = None
    turn: ChatTurnDetail | None = None


class ChatTurnDetailResponse(BaseModel):
    turn: ChatTurnDetail
