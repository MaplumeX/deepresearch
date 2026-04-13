from __future__ import annotations

from app.services.dedupe import dedupe_findings


def merge_evidence(state: dict) -> dict:
    sources = dict(state.get("sources", {}))
    for batch in state.get("raw_source_batches", []):
        sources.update(batch)
    findings = dedupe_findings(list(state.get("raw_findings", [])))
    return {
        "findings": findings,
        "sources": sources,
    }

