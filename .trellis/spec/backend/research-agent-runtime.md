# Research Agent Runtime

> Executable contracts for the Python deep research backend scaffold.

---

## Scenario: Python Deep Research Backend Scaffold

### 1. Scope / Trigger
- Trigger: backend work that changes LangGraph state, research workflow nodes, runtime persistence, API payloads, or tool integrations.
- Scope: `app/graph/`, `app/runtime.py`, `app/api/`, `app/tools/`, and request/report contracts.

### 2. Signatures

#### API

```python
POST /api/research/runs
GET /api/research/runs
GET /api/research/runs/{run_id}
GET /api/research/runs/{run_id}/events
POST /api/research/runs/{run_id}/resume
GET /api/conversations
GET /api/conversations/{conversation_id}
DELETE /api/conversations/{conversation_id}
POST /api/conversations
POST /api/conversations/{conversation_id}/messages
GET /api/chat/turns/{turn_id}
GET /api/chat/turns/{turn_id}/events
GET /health
```

#### Runtime

```python
async def run_research(
    request_payload: dict[str, Any],
    run_id: str,
    memory: dict[str, Any] | None = None,
) -> dict[str, Any]
async def resume_research(run_id: str, resume_payload: dict[str, Any]) -> dict[str, Any]
class ResearchRunManager:
    async def create_run(request_payload: dict[str, Any]) -> ResearchRunDetail
    async def create_conversation(request_payload: dict[str, Any]) -> tuple[ResearchConversationDetail, ResearchRunDetail]
    async def create_message(conversation_id: str, request_payload: dict[str, Any]) -> tuple[ResearchConversationDetail, ResearchRunDetail]
    async def resume_run(run_id: str, resume_payload: dict[str, Any]) -> ResearchRunDetail
    def get_run(run_id: str) -> ResearchRunDetail
    def list_runs() -> list[ResearchRunSummary]
    def get_conversation(conversation_id: str) -> ResearchConversationDetail
    def list_conversations() -> list[ResearchConversationSummary]

class ChatConversationManager:
    async def create_conversation(request_payload: dict[str, Any]) -> tuple[ResearchConversationDetail, ChatTurnDetail]
    async def create_message(conversation_id: str, request_payload: dict[str, Any]) -> tuple[ResearchConversationDetail, ChatTurnDetail]
    def get_turn(turn_id: str) -> ChatTurnDetail
    async def stream_events(turn_id: str) -> AsyncIterator[str]
```

#### Graph Nodes

```python
def ingest_request(state: dict) -> dict
def plan_research(state: dict) -> dict
async def research_worker(state: dict) -> dict
def merge_evidence(state: dict) -> dict
def gap_check(state: dict) -> dict
def synthesize_report_node(state: dict) -> dict
def citation_audit(state: dict) -> dict
```

#### Worker Internal Stages

```python
def rewrite_queries_node(state: dict) -> dict
async def search_and_rank_node(state: dict) -> dict
async def acquire_and_filter_node(state: dict) -> dict
def extract_and_score_node(state: dict) -> dict
def emit_results_node(state: dict) -> dict
```

### 3. Contracts

#### Request Contract

```json
{
  "question": "string, required, non-empty",
  "scope": "string, optional",
  "output_language": "zh-CN | en",
  "max_iterations": "int, 1..5",
  "max_parallel_tasks": "int, 1..5"
}
```

#### Conversation Turn Request Contract

```json
{
  "question": "string, required, non-empty",
  "scope": "string, optional",
  "output_language": "zh-CN | en",
  "max_iterations": "int, 1..5",
  "max_parallel_tasks": "int, 1..5",
  "parent_run_id": "string, optional, follow-up source run inside the same conversation"
}
```

#### Conversation Create Request Contract

```json
{
  "mode": "chat | research",
  "question": "string, required, non-empty",
  "scope": "string, optional, research only",
  "output_language": "zh-CN | en | null, research only",
  "max_iterations": "int, 1..5 or null, research only",
  "max_parallel_tasks": "int, 1..5 or null, research only"
}
```

#### Run Status Contract

```json
["queued", "running", "interrupted", "completed", "failed"]
```

#### Run Detail Contract

```json
{
  "run_id": "string",
  "conversation_id": "string",
  "origin_message_id": "string",
  "assistant_message_id": "string",
  "parent_run_id": "string or null",
  "status": "queued | running | interrupted | completed | failed",
  "request": "normalized request payload",
  "result": "graph state snapshot or null",
  "warnings": "flattened warnings extracted from result",
  "error_message": "string or null",
  "created_at": "ISO-8601 timestamp",
  "updated_at": "ISO-8601 timestamp",
  "completed_at": "ISO-8601 timestamp or null",
  "progress_events": [
    {
      "event_type": "run.created | run.status_changed | run.progress | run.interrupted | run.completed | run.failed | run.resumed",
      "status": "queued | running | interrupted | completed | failed",
      "timestamp": "ISO-8601 timestamp",
      "message": "string or null",
      "progress": "structured progress payload or null"
    }
  ]
}
```

`result` keeps the raw graph snapshot. For report-centric consumers, the stable fields are:

```json
{
  "draft_report": "markdown draft for compatibility and conversation history",
  "draft_structured_report": {
    "title": "string",
    "summary": "markdown summary block",
    "markdown": "rendered markdown assembled from structured sections",
    "sections": [
      {
        "section_id": "stable slug",
        "heading": "section heading",
        "body_markdown": "section markdown body",
        "cited_source_ids": "ordered citation ids used in this section"
      }
    ],
    "cited_source_ids": "ordered citation ids used in evidence-bearing sections",
    "citation_index": [
      {
        "source_id": "string",
        "title": "string",
        "url": "string",
        "snippet": "best evidence or source snippet",
        "providers": "list[str]",
        "acquisition_method": "provider_raw_content | http_fetch | jina_reader | firecrawl_scrape | search_snippet | null",
        "cited_in_sections": "list[str] of section ids",
        "occurrence_count": "int >= 0",
        "relevance_score": "float 0..1 or null",
        "confidence": "float 0..1 or null"
      }
    ],
    "source_cards": [
      {
        "source_id": "string",
        "title": "string",
        "url": "string",
        "snippet": "best evidence or source snippet",
        "providers": "list[str]",
        "acquisition_method": "provider_raw_content | http_fetch | jina_reader | firecrawl_scrape | search_snippet | null",
        "fetched_at": "ISO-8601 timestamp or empty string",
        "is_cited": "bool"
      }
    ]
  },
  "final_report": "final markdown output after optional human review",
  "final_structured_report": "same shape as draft_structured_report, regenerated if a human edits the markdown"
}
```

Implementation path for the structured report contract:

- `app/services/synthesis.py::synthesize_report()` builds the report draft and delegates final normalization.
- `app/services/report_contract.py::get_report_labels()` is the single source of truth for localized fixed report labels.
- `app/services/report_contract.py::build_structured_report()` is the canonical constructor for `draft_structured_report`.
- `app/services/report_contract.py::derive_structured_report()` is the canonical recovery path when human review edits raw markdown.
- `app/graph/nodes/synthesize.py::synthesize_report_node()` passes `request.output_language`, then writes `draft_report` and `draft_structured_report`.
- `app/graph/nodes/audit.py::citation_audit()` validates markdown + structured-report consistency.
- `app/graph/nodes/review.py::human_review()` regenerates `final_structured_report` from edited markdown and falls back to a localized title via `default_report_title()`.
- `web/src/types/research.ts` mirrors the backend payload shape.
- `web/src/components/ChatArea.tsx` is the current frontend boundary for rendering report markdown and linkifying citation badges from `source_cards`.

Synthesis budget and staged generation contract:

#### Scope / Trigger

- Trigger: `app/services/synthesis.py` changes that affect prompt size, section generation strategy, or `Settings` env keys controlling synthesis limits.
- Scope: `app/config.py`, `app/services/synthesis.py`, `app/graph/nodes/synthesize.py`, and `tests/unit/test_synthesis.py`.

#### Signatures

```python
def synthesize_report(
    question: str,
    tasks: list[dict],
    findings: list[dict],
    sources: dict[str, dict],
    settings: Settings,
    *,
    coverage_requirements: list[dict] | None = None,
    memory: dict[str, Any] | None = None,
    output_language: str | None = None,
) -> StructuredReport

def assign_report_headings(
    question: str,
    tasks: list[dict],
    findings: list[dict],
    settings: Settings,
    output_language: str | None = None,
) -> list[dict]

def build_structured_report(
    draft: ReportDraft,
    sources: dict[str, dict],
    findings: list[dict],
    output_language: str | None = None,
) -> StructuredReport

def get_report_labels(output_language: str | None) -> ReportLabels

def _build_compact_payload(
    question: str,
    tasks: list[dict],
    coverage_requirements: list[dict],
    findings: list[dict],
    sources: dict[str, dict],
    memory_brief: str,
    *,
    heading: str | None = None,
    purpose: str | None = None,
    focus: str | None = None,
) -> CompactPayload

def _maybe_synthesize_single_call(
    question: str,
    payload: CompactPayload,
    settings: Settings,
    labels: ReportLabels,
) -> ReportDraft | None

def _maybe_synthesize_multi_stage(
    question: str,
    tasks: list[dict],
    coverage_requirements: list[dict] | None,
    findings: list[dict],
    sources: dict[str, dict],
    settings: Settings,
    memory_brief: str,
    labels: ReportLabels,
) -> ReportDraft | None
```

#### Contracts

Runtime env keys in `app/config.py`:

```text
SYNTHESIS_SOFT_CHAR_LIMIT
SYNTHESIS_HARD_CHAR_LIMIT
SYNTHESIS_MAX_FINDINGS_PER_CALL
SYNTHESIS_MAX_SOURCES_PER_CALL
```

Compact payload rules:

- `_build_compact_payload()` is the only allowed path for LLM synthesis input in `app/services/synthesis.py`.
- `CompactPayload.tasks[*]` must contain only:
  `task_id`, `title`, `report_heading`, `question`
- `CompactPayload.coverage_requirements[*]` must contain only:
  `requirement_id`, `heading`, `description`, `coverage_tags`
- `CompactPayload.sources[*]` must contain only:
  `source_id`, `title`, `url`, `snippet`, `providers`, `source_role`
- `CompactPayload.findings[*]` must contain only:
  `task_id`, `source_id`, `claim`, `snippet`, `evidence_type`, `source_role`, `confidence`, `relevance_score`, `title`, `url`
- Raw `sources[*].content` must not be passed through to the prompt as a top-level field. If no snippet exists, a trimmed snippet may be derived from content inside `_build_compact_sources()`.

Localized fixed-label rules:

- `output_language == "en"` must default fixed labels to:
  `Research Report`, `Summary`, `Risks and Limitations`, `Conclusion`, `References`
- `output_language == "zh-CN"` or `None` must default fixed labels to:
  `研究报告`, `摘要`, `风险与局限`, `结论`, `参考资料`
- `build_structured_report()` must prepend the localized summary heading when `draft.summary` is non-empty.
- `render_structured_report_markdown()` must always append a localized references section, even when no cited sources exist.
- `derive_structured_report()` must preserve compatibility with edited markdown that uses legacy headings:
  summary headings: `Summary`, `Executive Summary`, `摘要`
  reference headings: `References`, `Sources`, `参考资料`

Default report-structure rules:

- Final report defaults must be:
  localized summary section
  zero or more rubric-based chapters derived from `coverage_requirements` when present and supported by evidence; otherwise task-based chapters derived from `task.report_heading`
  optional localized risk section when `evidence_type in {"risk", "limitation"}` and no rubric chapter already reserves the risk/tradeoff dimension
  localized conclusion section
  localized references section
- `synthesize_report()` must not inject `Conversation Context` or `Open Questions` into the final default report output.
- Rubric chapter ordering must follow `coverage_requirements`; task chapter ordering is used when no rubric chapters are emitted; both paths still end with risk section when needed, then conclusion.
- `assign_report_headings()` is the only allowed path for generating `task.report_heading` values before report synthesis.
- `task.title` remains the internal execution title for query rewriting, evidence extraction, and worker diagnostics; synthesis-only heading generation must not overwrite it.
- Invalid or duplicate generated report headings must fail the synthesis path instead of silently falling back to normalized task titles.

Routing rules:

- If `payload.estimated_size <= settings.synthesis_soft_char_limit` and the payload stays within `synthesis_max_findings_per_call` plus `synthesis_max_sources_per_call`, `synthesize_report()` may call `_maybe_synthesize_single_call()`.
- If the compact payload exceeds the soft limit or record-count limits, `synthesize_report()` must switch to `_maybe_synthesize_multi_stage()`.
- Multi-stage synthesis must split by semantic report sections first, not by arbitrary character ranges. Current default section groups are:
  rubric-based chapters when coverage requirements are available, otherwise task-based chapters, then localized risk section when needed, then localized conclusion section
- If a section chunk still exceeds `settings.synthesis_hard_char_limit`, synthesis must fail explicitly instead of rendering a deterministic section.
- `build_structured_report()` still receives the original `sources` and `findings` so citation auditing and source cards remain based on canonical state, not the compact prompt payload.

#### Validation & Error Matrix

| Condition | Validation point | Behavior |
|-----------|------------------|----------|
| `findings` is empty | `synthesize_report()` | raise `InsufficientEvidenceError` |
| compact payload exceeds `SYNTHESIS_SOFT_CHAR_LIMIT` or item-count limits | `_should_keep_payload_together()` | skip single-call synthesis and route to `_maybe_synthesize_multi_stage()` |
| staged chunk exceeds `SYNTHESIS_HARD_CHAR_LIMIT` | `_can_invoke_payload()` | raise `LLMOutputInvalidError` for oversized synthesis input |
| LLM import or invoke fails during single-call synthesis | `_maybe_synthesize_single_call()` | raise `LLMInvocationError`; caller may retry with staged LLM synthesis only |
| LLM import or invoke fails during staged synthesis | `_maybe_synthesize_section_with_llm()` | raise `LLMInvocationError`; caller must fail the run |
| compact source payload includes raw `content` field | `tests/unit/test_synthesis.py::test_compact_payload_excludes_raw_source_content` | fail the unit test; this shape is forbidden |
| `output_language` is `zh-CN` or omitted | `get_report_labels()` | use Chinese fixed report labels for title, summary, risk, conclusion, and references |
| `output_language` is `en` | `get_report_labels()` | use English fixed report labels for title, summary, risk, conclusion, and references |
| generated `task.report_heading` is empty, duplicates another task heading, or collides with a fixed report section heading | `assign_report_headings()` | raise `LLMOutputInvalidError` |

Structured report validation and error matrix:

| Condition | Validation point | Warning / behavior | Review required |
|-----------|------------------|--------------------|-----------------|
| `draft_report` is empty | `app/graph/nodes/audit.py::citation_audit()` | append `Draft report is empty.` | No by itself; escalates only if another gate also fails |
| findings exist but markdown has no `[S...]` citation | `has_citations(draft_report)` in `citation_audit()` | append `Draft report does not include inline citations.` | Yes in practice, because section-level citation validation also fails |
| markdown references a `source_id` not present in `sources` | `find_missing_citations(draft_report, sources)` | append `Draft report references unknown citations: ...` | Yes |
| structured report has no sections while findings exist | `_validate_structured_report()` in `citation_audit()` | append `Structured report does not include any sections.` | Yes |
| summary section with heading `Summary`, `Executive Summary`, or `摘要` exists but has no citation | `_validate_structured_report()` in `citation_audit()` | append `Summary does not include inline citations.` | Yes |
| non-background analysis section has content but no citation | `_validate_structured_report()` in `citation_audit()` | append `Section '<heading>' does not include inline citations.` | Yes |
| `cited_source_ids` and `citation_index[*].source_id` diverge | `_validate_structured_report()` in `citation_audit()` | append `Structured report citation index is out of sync with cited sources.` | Yes |

Good / Base / Bad cases for this contract:

- Good:
  `synthesize_report_node()` produces `draft_report` plus `draft_structured_report`, every evidence-bearing section contains `[S...]`, and `citation_index` / `source_cards` reflect the same cited sources.
- Good:
  synthesis input is compacted first, the report stays under prompt limits, the LLM returns a single structured draft without exposing raw source content in the prompt payload, and fixed headings follow `request.output_language`.
- Base:
  Human review edits markdown via `edited_report`; `human_review()` accepts the markdown and rebuilds `final_structured_report` with `derive_structured_report()` so the final payload is still structured.
- Base:
  single-call synthesis is too large, so `_maybe_synthesize_multi_stage()` generates task/risk/conclusion drafts and structured merge logic assembles the final report while preserving citations.
- Base:
  human-edited markdown still uses `Executive Summary`; `derive_structured_report()` must treat it as the summary section during rebuild.
- Bad:
  Markdown includes `"[Sdeadbeef]"` that does not exist in `sources`, or an analysis section omits citations while findings exist; `citation_audit()` must append warnings and set `review_required = True`.
- Bad:
  `app/services/synthesis.py` sends the entire `sources` dict including full `content` bodies directly to the LLM, which can trigger upstream `Input length exceeds the maximum length` failures and breaks the compact-payload contract.
- Bad:
  default synthesis emits `Conversation Context` as a visible report chapter, which leaks continuity-only memory into the final report structure instead of keeping it prompt-only.

Required tests and assertion points for this contract:

- `tests/unit/test_synthesis.py`
  Assert synthesis output includes `markdown`, `sections`, `citation_index`, and `source_cards`.
- `tests/unit/test_synthesis.py`
  Assert `_build_compact_payload()` excludes raw source `content` from prompt payloads.
- `tests/unit/test_synthesis.py`
  Assert fallback synthesis uses localized summary + task chapters + localized conclusion instead of `Conversation Context` or `Key Findings`.
- `tests/unit/test_synthesis.py`
  Assert `assign_report_headings()` preserves `task.title` and populates `task.report_heading`.
- `tests/unit/test_config.py`
  Assert synthesis budget env defaults load from `Settings`.
- `tests/unit/test_audit.py`
  Assert missing section citations trigger warnings and `review_required = True`.
- `tests/unit/test_synthesis.py`
  Assert synthesis switches to staged generation when `synthesis_soft_char_limit` is exceeded and keeps the report-style section layout.
- `tests/unit/test_synthesis.py`
  Assert `output_language="zh-CN"` localizes title and fixed headings.
- `tests/unit/test_audit.py`
  Assert `Summary` heading is accepted by citation audit and does not trigger a false positive.

#### Wrong vs Correct

Wrong:

```python
chain.invoke(
    {
        "question": question,
        "tasks": tasks,
        "findings": findings,
        "sources": sources,
    }
)
```

- Problem: full source bodies leak into the prompt, prompt size becomes unbounded, and a long run can fail before report generation starts.

Correct:

```python
payload = _build_compact_payload(question, tasks, findings, sources, memory_brief)
labels = get_report_labels(output_language)
if _should_keep_payload_together(payload, settings):
    drafted = _maybe_synthesize_single_call(question, payload, settings, labels)
else:
    drafted = _maybe_synthesize_multi_stage(
        question,
        tasks,
        findings,
        sources,
        settings,
        memory_brief,
        labels,
    )
```

- Reason: prompt size is bounded before LLM invocation, fixed labels stay aligned with `output_language`, single-call synthesis remains the fast path, and large reports degrade to staged synthesis instead of provider-side length errors.

#### Conversation Message Contract

```json
{
  "message_id": "string",
  "conversation_id": "string",
  "role": "user | assistant",
  "content": "string, may be empty while assistant run is still pending",
  "run_id": "string or null",
  "parent_message_id": "string or null",
  "created_at": "ISO-8601 timestamp",
  "updated_at": "ISO-8601 timestamp"
}
```

#### Conversation Summary Contract

```json
{
  "conversation_id": "string",
  "mode": "chat | research",
  "title": "string",
  "latest_message_preview": "string",
  "latest_run_status": "queued | running | interrupted | completed | failed | null",
  "created_at": "ISO-8601 timestamp",
  "updated_at": "ISO-8601 timestamp"
}
```

#### Conversation Detail Contract

```json
{
  "conversation_id": "string",
  "mode": "chat | research",
  "title": "string",
  "latest_message_preview": "string",
  "latest_run_status": "queued | running | interrupted | completed | failed | null",
  "created_at": "ISO-8601 timestamp",
  "updated_at": "ISO-8601 timestamp",
  "messages": "conversation message list ordered by creation time",
  "runs": "run detail list ordered by creation time"
}
```

#### Conversation Delete Contract

```json
{
  "success": {
    "status": "ok"
  },
  "not_found": "404 when the conversation does not exist",
  "active_work_conflict": "409 when any research run or chat turn in the conversation is still queued or running"
}
```

#### Conversation Memory Contract

```json
{
  "rolling_summary": "string, compressed background context for turns older than the recent 5-run window",
  "recent_turns": [
    {
      "run_id": "string",
      "question": "string",
      "answer_digest": "string",
      "status": "queued | running | interrupted | completed | failed",
      "created_at": "ISO-8601 timestamp"
    }
  ],
  "key_facts": [
    {
      "fact": "string",
      "source_ids": "list[str]"
    }
  ],
  "open_questions": "list[str]"
}
```

#### SSE Event Contract

```json
{
  "type": "run.created | run.status_changed | run.progress | run.interrupted | run.completed | run.failed | run.resumed",
  "run_id": "string",
  "status": "current run status",
  "timestamp": "ISO-8601 timestamp",
  "data": {
    "message": "optional string",
    "progress": {
      "phase": "queued | clarifying_scope | planning | executing_tasks | merging_evidence | checking_gaps | replanning | synthesizing | auditing | awaiting_review | finalizing | completed | failed",
      "phase_label": "human-readable label",
      "iteration": "int or null",
      "max_iterations": "int or null",
      "task": {
        "task_id": "string",
        "title": "string",
        "index": "int >= 1",
        "total": "int >= 1",
        "status": "pending | running | done | failed",
        "worker_step": "rewrite_queries | search_and_rank | acquire_and_filter | extract_and_score | emit_results | null"
      },
      "counts": {
        "planned_tasks": "int or null",
        "completed_tasks": "int or null",
        "search_hits": "int or null",
        "acquired_contents": "int or null",
        "kept_sources": "int or null",
        "evidence_count": "int or null",
        "warnings": "int or null"
      },
      "action": {
        "kind": "targeted_retry | replan | review",
        "label": "short UI label for the current decision",
        "detail": "short explanation for why the workflow is retrying, replanning, or waiting"
      },
      "gaps": [
        {
          "task_id": "task id or coverage requirement id",
          "title": "short gap title",
          "gap_type": "missing_evidence | weak_evidence | low_source_diversity | retrieval_failure | coverage_gap",
          "severity": "low | medium | high",
          "retry_action": "expand_queries | expand_fetch | replan | null",
          "scope": "task | global"
        }
      ],
      "retry_tasks": [
        {
          "task_id": "pending retry task id",
          "title": "task title",
          "retry_action": "expand_queries | expand_fetch | replan | null",
          "retry_count": "int >= 0",
          "query_budget": "int or null",
          "fetch_budget": "int or null"
        }
      ],
      "review": {
        "required": "bool",
        "kind": "human_review | null"
      }
    },
    "run": "optional run detail snapshot",
    "conversation": "optional conversation summary snapshot",
    "assistant_message": "optional assistant message snapshot for the affected run"
  }
}
```

- `progress.action` is optional and should only be present when the runtime can explain a concrete next step such as targeted retry, replanning, or human review.
- `progress.gaps` is a compact explanation list for UI display; it does not replace the canonical `GraphState["gaps"]`.
- `progress.retry_tasks` should only include currently pending targeted retries, not every task in the run.

#### Chat Turn Event Contract

```json
{
  "type": "chat.turn.created | chat.turn.status_changed | chat.turn.completed | chat.turn.failed",
  "turn_id": "string",
  "status": "queued | running | completed | failed",
  "timestamp": "ISO-8601 timestamp",
  "data": {
    "message": "optional string",
    "turn": "optional chat turn snapshot",
    "conversation": "optional conversation summary snapshot",
    "assistant_message": "optional assistant message snapshot for the affected turn"
  }
}
```

#### Persistence Contract

```text
conversations(
  conversation_id PK,
  mode,
  title,
  created_at,
  updated_at
)

conversation_messages(
  message_id PK,
  conversation_id,
  role,
  content,
  run_id nullable,
  parent_message_id nullable,
  created_at,
  updated_at
)

research_runs(
  run_id PK,
  conversation_id,
  origin_message_id,
  assistant_message_id,
  parent_run_id nullable,
  status,
  request_json,
  result_json nullable,
  error_message nullable,
  created_at,
  updated_at,
  completed_at nullable
)

research_run_events(
  event_id PK,
  run_id,
  conversation_id,
  sequence_no,
  event_type,
  status,
  timestamp,
  message nullable,
  progress_json nullable
)

chat_turns(
  turn_id PK,
  conversation_id,
  origin_message_id,
  assistant_message_id,
  status,
  request_json,
  error_message nullable,
  created_at,
  updated_at,
  completed_at nullable
)

conversation_memory(
  conversation_id PK,
  rolling_summary,
  key_facts_json,
  open_questions_json,
  updated_at
)
```

This store no longer auto-migrates pre-conversation legacy rows. If the on-disk schema predates `mode`, `conversation_id`, or message linkage columns, reset or migrate the database outside the app before startup.

#### Graph State Contract

```json
{
  "request": "normalized request payload",
  "memory": "conversation short-term memory payload with recent 5 runs plus persisted older summary",
  "tasks": "list of research tasks with optional report_heading",
  "coverage_requirements": "list of global answer-coverage requirements emitted by the planner",
  "raw_findings": "append-only list of worker evidence",
  "raw_source_batches": "append-only list of worker source maps",
  "task_outcomes": "append-only list of per-task worker diagnostics for the current and earlier iterations",
  "findings": "deduplicated evidence list",
  "sources": "source_id -> source document",
  "gaps": "list of structured follow-up research gaps",
  "quality_gate": "quality-gate decision after merge + gap analysis",
  "warnings": "report validation warnings",
  "draft_report": "markdown draft",
  "draft_structured_report": "structured report draft aligned with draft_report",
  "final_report": "final markdown output",
  "final_structured_report": "structured report aligned with final_report",
  "iteration_count": "completed planning rounds",
  "review_required": "whether interrupt-based review is required"
}
```

Task contract inside `GraphState["tasks"]`:

```json
{
  "task_id": "string",
  "title": "internal execution title used by retrieval/extraction flows",
  "report_heading": "optional synthesis-only chapter heading",
  "question": "string",
  "coverage_tags": "list[str], planner-assigned coverage intents such as scope/recent/risks",
  "query_budget": "int, 1..6, initial query budget for this task",
  "fetch_budget": "int, 1..10, initial ranked-hit fetch budget for this task",
  "retry_count": "int >= 0, targeted retry attempts already consumed for this task",
  "status": "pending | running | done | failed"
}
```

- `title` must stay stable across worker execution and gap recovery.
- `report_heading` may be populated during synthesis, but it must not replace `title` in retrieval, evidence extraction, or worker-quality services.
- `coverage_tags` are planner-owned hints used by quality and coverage checks; they are not user-authored request fields.
- `query_budget` and `fetch_budget` are execution controls, not user-visible report content.
- `retry_count` advances only for targeted task retries that return to `dispatch_tasks`; it does not replace graph-level `iteration_count`.

Coverage requirement contract inside `GraphState["coverage_requirements"]`:

```json
{
  "requirement_id": "stable planner-generated id",
  "title": "short rubric label",
  "description": "what a complete answer still needs to cover",
  "coverage_tags": "list[str], normalized tags used to match tasks and evidence"
}
```

#### Worker Task Outcome Contract

```json
{
  "task_id": "string",
  "title": "task title",
  "quality_status": "ok | weak | failed",
  "query_count": "int >= 0",
  "total_query_count": "int >= query_count, full query plan size before budgeting",
  "search_hit_count": "int >= 0",
  "acquired_content_count": "int >= 0",
  "kept_source_count": "int >= 0",
  "evidence_count": "int >= 0",
  "host_count": "int >= 0",
  "failure_reasons": "list[str]",
  "executed_queries": "list[str], query strings actually executed in this attempt",
  "used_urls": "list[str], ranked URLs consumed by the fetch stage in this attempt",
  "stage_status": "stage -> ok | failed map for rewrite/search/acquire/extract/emit"
}
```

#### Research Gap Contract

```json
{
  "gap_type": "missing_evidence | weak_evidence | low_source_diversity | retrieval_failure | coverage_gap",
  "task_id": "string",
  "title": "short follow-up title",
  "reason": "why the gap exists",
  "retry_hint": "deterministic suggestion for the next planning round",
  "severity": "low | medium | high",
  "retry_action": "expand_queries | expand_fetch | replan | null"
}
```

#### Quality Gate Contract

```json
{
  "passed": "bool",
  "should_replan": "bool",
  "requires_review": "bool",
  "reasons": "list[str], human-readable gate failures"
}
```

#### Worker Search Hit Contract

```json
{
  "title": "string",
  "url": "non-empty string",
  "snippet": "provider snippet or merged snippet",
  "providers": "list[str], provider ids that surfaced this url",
  "provider_metadata": "provider -> rank/query/native metadata map",
  "raw_content": "provider-supplied content when available",
  "raw_content_format": "html | text | markdown | null"
}
```

#### Worker Source Contract

```json
{
  "source_id": "stable hash-derived id",
  "url": "string",
  "title": "string",
  "content": "normalized main text",
  "fetched_at": "ISO-8601 timestamp",
  "providers": "list[str]",
  "acquisition_method": "provider_raw_content | http_fetch | jina_reader | firecrawl_scrape | search_snippet",
  "metadata": "provider/content metadata used for downstream reasoning"
}
```

#### Worker Fallback Fetch Contract

```python
async def acquire_contents(hits: list[SearchHit]) -> list[AcquiredContent]
async def fetch_with_jina_reader(
    contents: list[AcquiredContent],
    *,
    settings: Settings | None = None,
) -> dict[str, AcquiredContent]
async def fetch_with_firecrawl(
    contents: list[AcquiredContent],
    *,
    settings: Settings | None = None,
) -> dict[str, AcquiredContent]

def should_escalate_to_jina_reader(item: AcquiredContent) -> bool
def should_escalate_to_firecrawl(item: AcquiredContent) -> bool
def replace_contents(
    contents: list[AcquiredContent],
    replacements: dict[str, AcquiredContent],
) -> list[AcquiredContent]
```

```text
File paths:
- app/tools/fetch.py
- app/services/source_content.py
- app/graph/subgraphs/research_worker.py
```

#### Worker Fallback Metadata Contract

`AcquiredContent.metadata` may now include the following normalized keys after local or remote fetch:

```json
{
  "provider_metadata": "dict[str, dict]",
  "content_type": "HTTP content-type string when available",
  "response_url": "final URL after redirects when available",
  "status_code": "HTTP status code when available",
  "extracted_text": "normalized extracted text used for filtering/scoring",
  "extractor": "passthrough | selectolax | trafilatura | readability-lxml | regex | cached-*",
  "interstitial_markers": ["captcha | access_denied | verify_human | enable_javascript | wechat_client_required | content_unavailable"],
  "quality_failure_reason": "empty_content | short_content | blocked_page | null",
  "fallback_provider": "jina_reader | firecrawl | null",
  "fallback_source_method": "provider_raw_content | http_fetch | jina_reader | null",
  "fallback_reason": "empty_content | short_content | blocked_page | null",
  "firecrawl_metadata": "provider payload metadata when Firecrawl returns it"
}
```

#### Worker Fallback Routing Contract

```text
Tier 0: provider_raw_content stays in-process when sufficiently long
Tier 1: http_fetch acquires raw page content and local extraction metadata
Tier 2: jina_reader runs only when should_escalate_to_jina_reader(item) is true
Tier 3: firecrawl_scrape runs only when should_escalate_to_firecrawl(item) is true after Tier 2
```

Escalation rule:

```text
quality_failure_reason in {empty_content, short_content, blocked_page}
AND acquisition_method in {provider_raw_content, http_fetch}        -> Jina Reader candidate
AND acquisition_method in {provider_raw_content, http_fetch, jina_reader} -> Firecrawl candidate
```

Replacement rule:

```text
replace_contents() must preserve original ordering by URL.
Only URLs present in the replacement map are swapped.
```

### Scenario: Article Fetch Fallback Routing

#### 1. Scope / Trigger
- Trigger: changes to article acquisition, remote fetch fallback, extraction metadata, or env keys that control Jina Reader / Firecrawl usage.
- Scope: `app/tools/fetch.py`, `app/services/source_content.py`, `app/graph/subgraphs/research_worker.py`, `app/tools/extract.py`, `app/config.py`, and any tests that assert acquisition order or method.

#### 2. Signatures
- `app/graph/subgraphs/research_worker.py::acquire_and_filter_node(state, config=None) -> dict`
- `app/tools/fetch.py::acquire_contents(hits) -> list[AcquiredContent]`
- `app/tools/fetch.py::fetch_with_jina_reader(contents, settings=None) -> dict[str, AcquiredContent]`
- `app/tools/fetch.py::fetch_with_firecrawl(contents, settings=None) -> dict[str, AcquiredContent]`
- `app/services/source_content.py::should_escalate_to_jina_reader(item) -> bool`
- `app/services/source_content.py::should_escalate_to_firecrawl(item) -> bool`
- `app/services/source_content.py::replace_contents(contents, replacements) -> list[AcquiredContent]`

#### 3. Contracts
- `Settings.enable_jina_reader_fallback`:
  defaults to `true` when `JINA_API_KEY` exists, otherwise `false`.
- `Settings.enable_firecrawl_fallback`:
  defaults to `true` when `FIRECRAWL_API_KEY` exists, otherwise `false`.
- `fetch_with_jina_reader()`:
  returns a URL-keyed replacement map only for successful remote upgrades; failures return no replacement entry.
- `fetch_with_firecrawl()`:
  returns a URL-keyed replacement map only for successful remote upgrades; failures return no replacement entry.
- `acquire_and_filter_node()`:
  must call local `acquire_contents()` first, then optional Jina replacement, then optional Firecrawl replacement, then `filter_acquired_contents()`.
- `AcquiredContent.acquisition_method`:
  may be `provider_raw_content | http_fetch | jina_reader | firecrawl_scrape | search_snippet`.

#### 4. Validation & Error Matrix

| Condition | Jina Reader | Firecrawl | Expected Result |
|----------|-------------|-----------|-----------------|
| Local fetch quality OK | skip | skip | keep local content |
| Local fetch `short_content` and Jina disabled | skip | optional if enabled and candidate survives | keep local content until later filters |
| Local fetch `short_content`, Jina success | replace | run only if upgraded item still escalates | prefer Jina result |
| Jina returns `blocked_page` | replace with blocked result | run | Firecrawl gets the Jina-upgraded item |
| Jina request failure / empty body | no replacement | run against original candidate if still eligible | preserve candidate for Firecrawl |
| Firecrawl request failure / empty body | no replacement | n/a | preserve last available candidate |
| acquisition method is `search_snippet` | skip | skip | no remote escalation |

#### 5. Good/Base/Bad Cases

**Good**
- Local HTML extraction marks `quality_failure_reason=short_content`, Jina returns long markdown body, Firecrawl receives no candidates, final method is `jina_reader`.

**Base**
- Local HTML extraction is already acceptable, no remote provider is called, final method stays `http_fetch`.

**Bad**
- Firecrawl is called before Jina for a candidate that only has local `short_content`.
- `replace_contents()` reorders the content list and changes ranking semantics.
- `search_snippet` items are escalated to remote article fetch providers.

#### 6. Tests Required
- `tests/unit/test_source_content.py`
  - assert escalation predicates for `http_fetch`, `jina_reader`, and `search_snippet`
  - assert `replace_contents()` preserves order
- `tests/unit/test_research_worker_subgraph.py`
  - assert Jina runs before Firecrawl
  - assert Firecrawl receives the Jina-upgraded blocked candidate when Jina still fails quality
- `tests/unit/test_extract_tool.py`
  - assert blocked/interstitial article pages are dropped before evidence extraction
- `tests/unit/test_research_worker_service.py`
  - assert filtering uses `metadata.extracted_text` rather than raw HTML length

#### 7. Wrong vs Correct

##### Wrong
- Put fallback routing inside `app/tools/fetch.py::acquire_contents()` and hide when Jina / Firecrawl should run.
- Inspect raw HTML length inside the graph node and ignore normalized extraction metadata.

##### Correct
- Keep remote request mechanics in `app/tools/fetch.py`.
- Keep escalation predicates and content replacement helpers in `app/services/source_content.py`.
- Keep orchestration order explicit in `app/graph/subgraphs/research_worker.py::acquire_and_filter_node()`.

#### Environment Contract

```text
LLM_API_KEY              optional, preferred API key for OpenAI-compatible chat endpoints
LLM_BASE_URL             optional, preferred base URL for OpenAI-compatible chat endpoints
OPENAI_API_KEY           optional fallback alias for compatibility
OPENAI_BASE_URL          optional fallback alias for compatibility
TAVILY_API_KEY           optional, enables web search
BRAVE_API_KEY            optional, enables Brave Search aggregation
SERPER_API_KEY           optional, enables Serper (Google Search) aggregation
JINA_API_KEY             optional, increases Jina Reader quota and enables auth-backed fallback by default
FIRECRAWL_API_KEY        optional, enables Firecrawl scrape fallback
ENABLE_JINA_READER_FALLBACK optional, defaults to true when JINA_API_KEY is set
ENABLE_FIRECRAWL_FALLBACK  optional, defaults to true when FIRECRAWL_API_KEY is set
JINA_TIMEOUT_SECONDS     optional, timeout for Jina Reader fallback requests
FIRECRAWL_TIMEOUT_SECONDS optional, timeout for Firecrawl fallback requests
CHECKPOINT_DB_PATH       optional, defaults to research.db
RUNS_DB_PATH             optional, defaults to research_runs.db
DEFAULT_MAX_ITERATIONS   optional, defaults to 2
DEFAULT_MAX_PARALLEL_TASKS optional, defaults to 3
ENABLE_LLM_PLANNING      optional bool, defaults to true
ENABLE_LLM_SYNTHESIS     optional bool, defaults to true
REQUIRE_HUMAN_REVIEW     optional bool, defaults to false
```

### 4. Validation & Error Matrix

| Boundary | Input | Validation | Failure Behavior |
|----------|-------|------------|------------------|
| API -> ingest_request | `question`, limits, language | `ResearchRequest` validates non-empty question and bounded limits | Raise validation error before graph execution |
| create conversation API -> manager | validated create payload with explicit `mode` | dispatch to research or chat manager only after LLM readiness passes; create conversation, user message, assistant placeholder, and queued run/turn inside the same persistence boundary | return 503 when required LLM capabilities are unavailable; return 500 if storage fails after readiness passes |
| generic conversation list/detail API -> store | `conversation_id` optional | return both chat and research conversations with explicit `mode`; research details include `runs`, chat details return an empty `runs` list | return 404 when target conversation is missing |
| follow-up message API -> manager | `conversation_id`, question, optional `parent_run_id` | conversation must exist; conversation `mode` decides whether to call research or chat manager; explicit `parent_run_id` must belong to the same research conversation | return 404 for missing conversation; return 409 when source run is still active, belongs to another conversation, or the mode-specific manager rejects the request |
| follow-up manager -> memory builder | conversation detail, optional persisted conversation memory | build memory from the recent 5 runs; if the requested parent run falls outside the latest 5, force it into the window and recompute older summary on the fly | fall back to deterministic summary rebuild instead of dropping memory context |
| run store -> detail/list API | `run_id` or conversation/list query | run must exist for detail/event routes; conversation must exist for conversation routes | return 404 when target run or conversation is missing |
| ingest_request -> graph state | request payload + memory payload | Normalize integer budgets before Pydantic validation and normalize memory shape into explicit `rolling_summary/recent_turns/key_facts/open_questions` keys | Invalid request values are clamped first, then validated; missing memory fields become empty defaults |
| planner -> tasks | question + gaps + memory | Limit task count to `max_parallel_tasks`; assign iteration-scoped task ids such as `iter-2-task-1`; emit `coverage_requirements` and normalized task `coverage_tags`; use memory only as continuity context, never as evidence | fail the run when the planner LLM is unavailable or returns no valid tasks / coverage rubric |
| task -> worker query rewrite | task question + request scope | Build at most 6 deduplicated queries for a single task, each with intent + priority metadata; worker execution must respect `task.query_budget` | fail the task when the query-rewrite LLM is unavailable or returns fewer than 3 distinct queries |
| search -> acquire content | provider search hits | Merge duplicate URLs, keep provider metadata, require non-empty URL | Skip invalid hits and tolerate per-provider search failures |
| acquire content -> extract | provider search hits + ranked-hit fetch budget | Select at most `task.fetch_budget` ranked hits for acquisition; then try provider raw content first, then HTTP fetch, then snippet fallback | Skip unusable content and continue with any surviving acquisition path |
| extract -> evidence extraction | normalized source documents | build neutral candidate snippets, require the LLM to return verbatim-supported snippets, and keep only validated evidence items | fail the task when the extraction LLM is unavailable or returns invalid unsupported evidence |
| worker -> task outcome | task, queries, ranked hits, acquired contents, kept sources, evidence | derive deterministic quality diagnostics from counts and host diversity | never throw because evidence is weak; emit `quality_status=weak/failed` and failure reasons instead |
| merge -> gap_check | deduplicated findings + `task_outcomes` + current task list + planner coverage rubric | create structured task-local gaps, evaluate global coverage requirements, map retryable gaps to `expand_queries` or `expand_fetch`, and only replan when no targeted retry path remains | if retryable tasks remain and iteration budget exists, route back to `dispatch_tasks`; if only global coverage gaps remain and budget exists, replan; if budget is exhausted, continue to synthesis with warnings and force human review |
| synthesize -> audit | markdown report + memory | Require citations to map to existing `sources`; memory may appear only in a background section and may not introduce citations | Set warning and require review when unknown citation ids exist |
| run persistence -> conversation thread | run lifecycle updates | assistant message content mirrors final report, draft report, or failure text for the linked run | keep assistant placeholder empty while queued/running; update assistant message content on interrupt/completion/failure |
| terminal run -> conversation memory store | conversation detail after completion/interruption/failure | persist summary/facts/questions for turns outside the recent 5-run window | write empty memory payload when the conversation has 5 or fewer runs instead of skipping the row |
| review -> finalize | resume payload | Optional `edited_report` override only | Keep draft report when no edited report is supplied |
| resume API -> runtime | `approved`, optional `edited_report` | run must be in `interrupted` status before resume | return 409 if client resumes a non-interrupted run |
| runtime -> checkpoint saver | `CHECKPOINT_DB_PATH` and runtime sqlite dependency set | runtime adapter must patch `aiosqlite.Connection.is_alive()` when the installed `aiosqlite` version no longer exposes it but `langgraph-checkpoint-sqlite` still probes it | fail the run with a surfaced runtime error if checkpoint initialization still cannot complete after compatibility patching |
| store migration -> legacy runs | rows created before conversation support | missing conversation/message linkage is backfilled into one-run-one-conversation threads during initialization | preserve historical runs instead of dropping them or returning partial conversation payloads |
| SSE endpoint -> frontend | `run_id` event stream | run must exist and payload must stay JSON-safe | send keep-alive comments while waiting; close after terminal states including `interrupted`; include enough conversation metadata for cache patching and a structured `progress` payload for live cards |

### 5. Good/Base/Bad Cases

#### Good
- Request contains a valid question and optional limits.
- Create API returns queued run immediately.
- Creating a conversation also persists the first user message and assistant placeholder before the background run starts.
- Follow-up turns create a new run inside the same conversation and link the new user message to the previous assistant message.
- Follow-up turns inject memory with the recent 5 runs and persisted summary of older runs.
- If `parent_run_id` points to an older run outside the latest 5, that run is forced into the memory window.
- Query rewrite produces focused task queries.
- Tavily and Brave can both contribute hits for the same worker task.
- Provider raw content is used when available; HTTP fetch and snippet fallback cover the rest.
- Evidence scoring keeps only relevant sources and emits bounded scores.
- Worker emits task diagnostics even when a task produces zero findings.
- `gap_check` emits structured gaps with retry hints instead of opaque strings.
- If research quality is weak and iteration budget remains, the graph loops back to `plan_research`.
- If research quality is weak and budget is exhausted, synthesis still runs but the final run is forced through human review.
- Synthesis emits markdown with valid `[source_id]` citations.
- Audit passes without unknown citations.
- Detail API and SSE stream both reflect the same terminal snapshot, including the updated assistant message and conversation summary.

#### Base
- No OpenAI-compatible credentials are configured.
- Research and chat create endpoints reject the request before queuing background work.
- Worker query rewrite, ranking, filtering, and scoring still run deterministically inside `research_worker`, but they are no longer reachable without the required top-level LLM path.
- One search provider may be unavailable and the graph still completes from the surviving provider or with an empty-evidence report.
- Legacy string-shaped `gaps` in older run snapshots still degrade to readable open questions in conversation memory.
- Installed `aiosqlite` may omit `Connection.is_alive()` while checkpoint persistence still succeeds through the runtime compatibility shim.
- Browser refreshes during a running job and the frontend restores state via detail API before reopening SSE.
- Conversations with 5 or fewer runs persist an empty `rolling_summary` while still providing explicit recent turns.
- Chat mode requires model credentials; missing readiness fails at the create endpoint before a chat turn is persisted.

#### Bad
- Empty `question`.
- `max_iterations` or `max_parallel_tasks` outside the accepted range after normalization.
- Follow-up payload references a run from another conversation.
- Chat or research message flow targets a conversation id whose persisted `mode` does not match the requested execution path.
- Follow-up payload is sent while the latest source run is still `queued` or `running`.
- Planner or synthesizer treats conversation memory as a citation source.
- Report cites a source id that is not present in `sources`.
- Both providers fail or return unusable hits for all queries.
- Provider raw content, HTTP fetch, and snippet fallback all fail or stay too weak for evidence extraction.
- Replanning reuses bare `task-1` ids across iterations and mixes old findings with new follow-up tasks.
- Client attempts to resume a completed run.
- Server restarts while queued/running jobs exist and leaves stale statuses unmarked.

### 6. Tests Required

- Unit test `app/services/citations.py` for citation extraction and missing citation detection.
- Unit test `app/services/dedupe.py` for duplicate-evidence selection.
- Unit test `app/services/research_worker.py` for query rewrite, cross-provider search-hit ranking, content filtering, and evidence scoring.
- Unit test `app/services/research_quality.py` for task diagnostics, structured gap mapping, and quality-gate decisions.
- Unit test `app/tools/extract.py` for provider-aware content normalization.
- Unit test `app/graph/nodes/gap_check.py` for structured-gap output, replan routing, and review-on-budget-exhaustion behavior.
- Unit test research create paths reject missing LLM readiness before queueing work.
- Unit test `app/services/conversation_memory.py` for recent-5 windowing, parent-run inclusion, digest building, persisted older-summary generation, and structured-gap open-question extraction.
- Unit test `app/run_store.py` for persisted conversation threading, assistant message synchronization, and legacy linkage backfill.
- Unit test `app/run_store.py` for `conversation_memory` read/write behavior.
- Unit test `app/run_manager.py` for async lifecycle transitions, follow-up turn creation, memory injection, and resume rules.
- Unit test synthesis fails explicitly when findings are empty or report headings are invalid.
- Unit test `app/runtime.py` for sqlite checkpoint compatibility when `aiosqlite.Connection.is_alive()` is absent.
- Syntax compilation for `app/` and `tests/`.

### 7. Wrong vs Correct

#### Wrong

```python
async def create_message(conversation_id: str, request_payload: dict) -> tuple[ResearchConversationDetail, ResearchRunDetail]:
    parent_run_id = request_payload.get("parent_run_id")
    run_id = parent_run_id or uuid4().hex
    run = store.create_run(run_id, request_payload)
    return store.get_conversation(run_id), run
```

- Problem: product-level conversation state is faked by mutating or overloading a single run identity, so follow-up turns cannot be validated or rendered as a stable thread.

#### Correct: Stable Conversation Threading

```python
async def create_message(
    conversation_id: str,
    request_payload: dict,
) -> tuple[ResearchConversationDetail, ResearchRunDetail]:
    conversation = manager.get_conversation(conversation_id)
    parent_run_id = manager._resolve_parent_run_id(conversation, request_payload.get("parent_run_id"))
    conversation, run = store.create_conversation_turn(
        conversation_id=conversation_id,
        run_id=uuid4().hex,
        request=request_payload,
        origin_message_id=uuid4().hex,
        assistant_message_id=uuid4().hex,
        parent_run_id=parent_run_id,
    )
    return conversation, run
```

- Reason: conversation identity stays stable, each user turn gets a fresh run/checkpoint lifecycle, and the frontend can render a real thread without overloading a single run as both conversation and execution state.

#### Correct: Stable Conversation Threading With Memory Injection

```python
async def create_message(
    conversation_id: str,
    request_payload: dict,
) -> tuple[ResearchConversationDetail, ResearchRunDetail]:
    conversation = manager.get_conversation(conversation_id)
    persisted_memory = store.get_conversation_memory(conversation_id)
    parent_run_id = manager._resolve_parent_run_id(conversation, request_payload.get("parent_run_id"))
    memory = build_memory_context(
        conversation,
        persisted_memory,
        window_size=5,
        parent_run_id=parent_run_id,
    )
    conversation, run = manager._create_turn(
        conversation_id=conversation_id,
        request_payload=request_payload,
        title=None,
        parent_run_id=parent_run_id,
        memory_context=memory.model_dump(),
)
    return conversation, run
```

#### Wrong: String-Only Gap Loop

```python
def gap_check(state: dict) -> dict:
    gaps = []
    if not state["findings"]:
        gaps.append("Need more evidence")
    return {"gaps": gaps}
```

- Problem: downstream planning cannot distinguish missing search coverage, acquisition failure, weak evidence, or low corroboration, so every retry looks the same.

#### Correct: Structured Gaps With Quality Gate

```python
def gap_check(state: dict) -> dict:
    gaps = identify_research_gaps(
        tasks,
        task_outcomes,
        coverage_requirements=coverage_requirements,
    )
    quality_gate = evaluate_quality_gate(
        gaps,
        has_iteration_budget=iteration_count < request.max_iterations,
    )
    return {
        "gaps": [gap.model_dump() for gap in gaps],
        "quality_gate": quality_gate.model_dump(),
        "review_required": quality_gate.requires_review,
    }
```

- Reason: structured gaps preserve failure semantics for re-planning, while the quality gate makes the replan-vs-review decision explicit and testable.

- Reason: follow-up execution keeps stable thread identity and injects explicit short-term memory into the new run without changing public API payloads.
