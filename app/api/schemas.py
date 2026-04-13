from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.models import (
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


class ConversationTurnRequest(ResearchRequest):
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
    run: ResearchRunDetail
