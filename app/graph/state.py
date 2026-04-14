from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class GraphState(TypedDict, total=False):
    request: dict
    memory: dict
    tasks: list[dict]
    raw_findings: Annotated[list[dict], operator.add]
    raw_source_batches: Annotated[list[dict], operator.add]
    task_outcomes: Annotated[list[dict], operator.add]
    findings: list[dict]
    sources: dict[str, dict]
    gaps: list[dict]
    quality_gate: dict
    warnings: list[str]
    draft_report: str
    draft_structured_report: dict
    final_report: str
    final_structured_report: dict
    iteration_count: int
    review_required: bool
