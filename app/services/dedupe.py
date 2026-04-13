from __future__ import annotations


def _dedupe_key(item: dict) -> tuple[str, str, str]:
    claim = str(item.get("claim", "")).strip().lower()
    return str(item.get("task_id", "")), str(item.get("source_id", "")), claim


def dedupe_findings(findings: list[dict]) -> list[dict]:
    best_by_key: dict[tuple[str, str, str], dict] = {}
    for item in findings:
        key = _dedupe_key(item)
        current = best_by_key.get(key)
        score = float(item.get("confidence", 0)) + float(item.get("relevance_score", 0))
        if current is None:
            best_by_key[key] = item
            continue
        current_score = float(current.get("confidence", 0)) + float(current.get("relevance_score", 0))
        if score > current_score:
            best_by_key[key] = item
    return list(best_by_key.values())

