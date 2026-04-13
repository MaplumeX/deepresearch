from __future__ import annotations

from typing import Literal

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


class SearchHit(BaseModel):
    title: str
    url: str
    snippet: str = ""


class SourceDocument(BaseModel):
    source_id: str
    url: str
    title: str
    content: str
    fetched_at: str


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

