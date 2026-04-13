from __future__ import annotations

import re
from collections import OrderedDict
from typing import Any

from app.domain.models import (
    ConversationMemoryPayload,
    MemoryFact,
    PersistedConversationMemory,
    RecentTurnMemory,
    ResearchConversationDetail,
    ResearchRunDetail,
)


DEFAULT_MEMORY_WINDOW = 5
_MAX_DIGEST_CHARS = 300
_MAX_SUMMARY_CHARS = 800
_MAX_FACTS = 8
_MAX_OPEN_QUESTIONS = 5


def empty_memory_payload() -> ConversationMemoryPayload:
    return ConversationMemoryPayload()


def build_memory_context(
    conversation: ResearchConversationDetail,
    persisted: PersistedConversationMemory | None = None,
    *,
    window_size: int = DEFAULT_MEMORY_WINDOW,
    parent_run_id: str | None = None,
) -> ConversationMemoryPayload:
    message_map = {message.message_id: message for message in conversation.messages}
    default_recent_runs = _tail_runs(conversation.runs, window_size)
    recent_runs = _select_recent_runs(conversation.runs, window_size, parent_run_id)
    recent_run_ids = {run.run_id for run in recent_runs}
    older_runs = [run for run in conversation.runs if run.run_id not in recent_run_ids]

    recent_turns = [
        _build_recent_turn_memory(
            run,
            message_map[run.assistant_message_id].content if run.assistant_message_id in message_map else "",
        )
        for run in recent_runs
    ]

    if persisted is not None and _run_ids(recent_runs) == _run_ids(default_recent_runs):
        rolling_summary = persisted.rolling_summary
        key_facts = persisted.key_facts
        open_questions = persisted.open_questions
    else:
        rolling_summary = summarize_older_runs(older_runs)
        key_facts = collect_key_facts(older_runs)
        open_questions = collect_open_questions(older_runs)

    return ConversationMemoryPayload(
        rolling_summary=rolling_summary,
        recent_turns=recent_turns,
        key_facts=key_facts,
        open_questions=open_questions,
    )


def rebuild_persisted_memory(
    conversation: ResearchConversationDetail,
    *,
    window_size: int = DEFAULT_MEMORY_WINDOW,
) -> PersistedConversationMemory:
    older_runs = conversation.runs[:-window_size] if len(conversation.runs) > window_size else []
    return PersistedConversationMemory(
        conversation_id=conversation.conversation_id,
        rolling_summary=summarize_older_runs(older_runs),
        key_facts=collect_key_facts(older_runs),
        open_questions=collect_open_questions(older_runs),
        updated_at=conversation.updated_at,
    )


def build_turn_digest(run: ResearchRunDetail, answer_content: str = "") -> str:
    normalized_answer = _normalize_markdown(answer_content)
    if normalized_answer:
        return _trim_text(normalized_answer, _MAX_DIGEST_CHARS)

    if run.status == "failed":
        return _trim_text(run.error_message or "研究执行失败。", _MAX_DIGEST_CHARS)
    if run.status == "interrupted":
        return "研究暂停，等待人工审核。"
    if run.status in {"queued", "running"}:
        return "研究仍在执行。"

    if isinstance(run.result, dict):
        report = _first_non_empty(
            run.result.get("final_report"),
            run.result.get("draft_report"),
        )
        normalized_report = _normalize_markdown(report)
        if normalized_report:
            return _trim_text(normalized_report, _MAX_DIGEST_CHARS)
    return ""


def extract_memory_facts(run: ResearchRunDetail) -> list[MemoryFact]:
    if not isinstance(run.result, dict):
        return []

    facts: list[MemoryFact] = []
    seen: set[str] = set()
    raw_findings = run.result.get("findings", [])
    if not isinstance(raw_findings, list):
        return []

    for item in raw_findings:
        if not isinstance(item, dict):
            continue
        fact = _trim_text(
            _normalize_space(
                _first_non_empty(item.get("claim"), item.get("snippet")),
            ),
            220,
        )
        if not fact:
            continue
        dedupe_key = fact.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        source_id = _normalize_space(str(item.get("source_id", "")))
        facts.append(MemoryFact(fact=fact, source_ids=[source_id] if source_id else []))
        if len(facts) >= 3:
            break
    return facts


def extract_open_questions(run: ResearchRunDetail) -> list[str]:
    if not isinstance(run.result, dict):
        return []

    raw_gaps = run.result.get("gaps", [])
    if not isinstance(raw_gaps, list):
        return []

    questions: list[str] = []
    seen: set[str] = set()
    for gap in raw_gaps:
        text = _trim_text(_normalize_space(str(gap)), 180)
        if not text:
            continue
        dedupe_key = text.casefold()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        questions.append(text)
        if len(questions) >= 3:
            break
    return questions


def summarize_older_runs(runs: list[ResearchRunDetail]) -> str:
    if not runs:
        return ""

    lines: list[str] = []
    for run in runs:
        if run.status == "failed":
            continue
        question = _trim_text(_normalize_space(run.request.question), 120)
        answer = build_turn_digest(run)
        if not question and not answer:
            continue
        line = f"- Q: {question}"
        if answer:
            line += f" | A: {answer}"
        lines.append(_trim_text(line, 260))

    if not lines:
        return ""
    return _trim_text("\n".join(lines), _MAX_SUMMARY_CHARS)


def collect_key_facts(runs: list[ResearchRunDetail]) -> list[MemoryFact]:
    aggregated: "OrderedDict[str, MemoryFact]" = OrderedDict()
    for run in runs:
        for fact in extract_memory_facts(run):
            key = fact.fact.casefold()
            existing = aggregated.get(key)
            if existing is None:
                aggregated[key] = fact
            else:
                merged_source_ids = list(dict.fromkeys([*existing.source_ids, *fact.source_ids]))
                aggregated[key] = MemoryFact(fact=existing.fact, source_ids=merged_source_ids)
            if len(aggregated) >= _MAX_FACTS:
                break
        if len(aggregated) >= _MAX_FACTS:
            break
    return list(aggregated.values())


def collect_open_questions(runs: list[ResearchRunDetail]) -> list[str]:
    ordered_questions: OrderedDict[str, str] = OrderedDict()
    for run in runs:
        for question in extract_open_questions(run):
            key = question.casefold()
            ordered_questions.setdefault(key, question)
            if len(ordered_questions) >= _MAX_OPEN_QUESTIONS:
                break
        if len(ordered_questions) >= _MAX_OPEN_QUESTIONS:
            break
    return list(ordered_questions.values())


def format_memory_for_prompt(memory: dict[str, Any] | ConversationMemoryPayload | None) -> dict[str, str]:
    payload = ConversationMemoryPayload.model_validate(memory or {})
    recent_turns = "\n".join(
        [
            f"{index}. Q: {turn.question}\n   A: {turn.answer_digest}\n   Status: {turn.status}"
            for index, turn in enumerate(payload.recent_turns, start=1)
        ]
    ) or "None"
    key_facts = "\n".join(
        [
            f"- {fact.fact}" + (f" [{', '.join(fact.source_ids)}]" if fact.source_ids else "")
            for fact in payload.key_facts
        ]
    ) or "None"
    open_questions = "\n".join(f"- {item}" for item in payload.open_questions) or "None"
    return {
        "rolling_summary": payload.rolling_summary or "None",
        "recent_turns": recent_turns,
        "key_facts": key_facts,
        "open_questions": open_questions,
    }


def build_contextual_brief(
    memory: dict[str, Any] | ConversationMemoryPayload | None,
    *,
    max_chars: int = 400,
) -> str:
    payload = ConversationMemoryPayload.model_validate(memory or {})
    parts: list[str] = []
    if payload.rolling_summary:
        parts.append(f"Earlier context: {payload.rolling_summary}")
    if payload.recent_turns:
        latest_turn = payload.recent_turns[-1]
        parts.append(f"Most recent turn: Q: {latest_turn.question} A: {latest_turn.answer_digest}")
    if payload.open_questions:
        parts.append("Open questions: " + "; ".join(payload.open_questions[:2]))
    return _trim_text("\n".join(parts), max_chars)


def _build_recent_turn_memory(run: ResearchRunDetail, answer_content: str) -> RecentTurnMemory:
    return RecentTurnMemory(
        run_id=run.run_id,
        question=run.request.question,
        answer_digest=build_turn_digest(run, answer_content),
        status=run.status,
        created_at=run.created_at,
    )


def _select_recent_runs(
    runs: list[ResearchRunDetail],
    window_size: int,
    parent_run_id: str | None,
) -> list[ResearchRunDetail]:
    recent_runs = _tail_runs(runs, window_size)
    if not parent_run_id or parent_run_id in {run.run_id for run in recent_runs}:
        return recent_runs

    parent_run = next((run for run in runs if run.run_id == parent_run_id), None)
    if parent_run is None or not recent_runs:
        return recent_runs

    adjusted_runs = list(recent_runs[1:])
    adjusted_runs.append(parent_run)
    adjusted_runs.sort(key=lambda run: (run.created_at, run.run_id))
    return adjusted_runs


def _tail_runs(runs: list[ResearchRunDetail], window_size: int) -> list[ResearchRunDetail]:
    if window_size <= 0:
        return []
    if len(runs) <= window_size:
        return list(runs)
    return list(runs[-window_size:])


def _run_ids(runs: list[ResearchRunDetail]) -> list[str]:
    return [run.run_id for run in runs]


def _normalize_markdown(value: Any) -> str:
    lines = []
    for raw_line in str(value or "").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        stripped = re.sub(r"^[#>*\-\d\.\)\s]+", "", stripped)
        stripped = _normalize_space(stripped)
        if stripped:
            lines.append(stripped)
        if len(lines) >= 3:
            break
    return _normalize_space(" ".join(lines))


def _normalize_space(value: str) -> str:
    return " ".join(value.split()).strip()


def _trim_text(value: str, max_chars: int) -> str:
    normalized = _normalize_space(value)
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def _first_non_empty(*values: Any) -> str:
    for value in values:
        text = _normalize_space(str(value or ""))
        if text:
            return text
    return ""
