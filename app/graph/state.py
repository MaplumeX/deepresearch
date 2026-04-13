from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class GraphState(TypedDict, total=False):
    request: dict
    tasks: list[dict]
    raw_findings: Annotated[list[dict], operator.add]
    raw_source_batches: Annotated[list[dict], operator.add]
    findings: list[dict]
    sources: dict[str, dict]
    gaps: list[str]
    warnings: list[str]
    draft_report: str
    final_report: str
    iteration_count: int
    review_required: bool

