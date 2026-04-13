from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    question: str = Field(min_length=1)
    scope: str | None = None
    output_language: Literal["zh-CN", "en"] = "zh-CN"
    max_iterations: int = Field(default=2, ge=1, le=5)
    max_parallel_tasks: int = Field(default=3, ge=1, le=5)


class ResearchTask(BaseModel):
    task_id: str
    title: str
    question: str
    status: Literal["pending", "running", "done", "failed"] = "pending"


class ResearchPlan(BaseModel):
    tasks: list[ResearchTask]


ContentFormat = Literal["html", "text", "markdown"]
AcquisitionMethod = Literal["provider_raw_content", "http_fetch", "search_snippet"]


class SearchHit(BaseModel):
    title: str
    url: str
    snippet: str = ""
    providers: list[str] = Field(default_factory=list)
    provider_metadata: dict[str, dict[str, Any]] = Field(default_factory=dict)
    raw_content: str | None = None
    raw_content_format: ContentFormat | None = None


class AcquiredContent(BaseModel):
    url: str
    title: str
    content: str
    content_format: ContentFormat
    acquired_at: str
    providers: list[str] = Field(default_factory=list)
    acquisition_method: AcquisitionMethod
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceDocument(BaseModel):
    source_id: str
    url: str
    title: str
    content: str
    fetched_at: str
    providers: list[str] = Field(default_factory=list)
    acquisition_method: AcquisitionMethod = "http_fetch"
    metadata: dict[str, Any] = Field(default_factory=dict)


class Evidence(BaseModel):
    evidence_id: str
    task_id: str
    claim: str
    snippet: str
    source_id: str
    url: str
    title: str
    relevance_score: float = Field(default=0.5, ge=0, le=1)
    confidence: float = Field(default=0.5, ge=0, le=1)


class ReportDraft(BaseModel):
    title: str
    summary: str
    markdown: str
    cited_source_ids: list[str]


RunStatus = Literal["queued", "running", "interrupted", "completed", "failed"]
RunEventType = Literal[
    "run.created",
    "run.status_changed",
    "run.progress",
    "run.interrupted",
    "run.completed",
    "run.failed",
    "run.resumed",
]


class ResearchRunSummary(BaseModel):
    run_id: str
    status: RunStatus
    request: ResearchRequest
    error_message: str | None = None
    created_at: str
    updated_at: str
    completed_at: str | None = None


class ResearchRunDetail(ResearchRunSummary):
    result: dict[str, Any] | None = None
    warnings: list[str] = Field(default_factory=list)


class ResearchRunEvent(BaseModel):
    type: RunEventType
    run_id: str
    status: RunStatus
    timestamp: str
    data: dict[str, Any] = Field(default_factory=dict)
