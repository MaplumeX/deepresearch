from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    question: str = Field(min_length=1)
    scope: str | None = None
    output_language: Literal["zh-CN", "en"] = "zh-CN"
    max_iterations: int | None = Field(default=None, ge=1, le=5)
    max_parallel_tasks: int | None = Field(default=None, ge=1, le=5)


class ResumeRequest(BaseModel):
    approved: bool = True
    edited_report: str | None = None


class RunResponse(BaseModel):
    run_id: str
    status: Literal["completed", "interrupted"]
    result: dict[str, Any]

