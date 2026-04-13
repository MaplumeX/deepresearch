from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter

from app.api.schemas import ResumeRequest, RunRequest, RunResponse
from app.runtime import resume_research, run_research


router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/research/runs", response_model=RunResponse)
async def create_run(request: RunRequest) -> RunResponse:
    run_id = uuid4().hex
    result = await run_research(
        request.model_dump(exclude_none=True),
        run_id=run_id,
    )
    status = "interrupted" if "__interrupt__" in result else "completed"
    return RunResponse(run_id=run_id, status=status, result=result)


@router.post("/api/research/runs/{run_id}/resume", response_model=RunResponse)
async def resume_run(run_id: str, request: ResumeRequest) -> RunResponse:
    result = await resume_research(
        run_id=run_id,
        resume_payload=request.model_dump(exclude_none=True),
    )
    status = "interrupted" if "__interrupt__" in result else "completed"
    return RunResponse(run_id=run_id, status=status, result=result)

