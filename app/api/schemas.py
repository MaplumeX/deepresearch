from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.models import ResearchRequest, ResearchRunDetail, ResearchRunSummary


class RunRequest(ResearchRequest):
    pass


class ResumeRequest(BaseModel):
    approved: bool = True
    edited_report: str | None = None


class RunDetailResponse(BaseModel):
    run: ResearchRunDetail


class RunListResponse(BaseModel):
    runs: list[ResearchRunSummary]
