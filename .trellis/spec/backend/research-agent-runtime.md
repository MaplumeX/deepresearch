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
        "acquisition_method": "provider_raw_content | http_fetch | search_snippet | null",
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
        "acquisition_method": "provider_raw_content | http_fetch | search_snippet | null",
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
- `app/services/report_contract.py::build_structured_report()` is the canonical constructor for `draft_structured_report`.
- `app/services/report_contract.py::derive_structured_report()` is the canonical recovery path when human review edits raw markdown.
- `app/graph/nodes/synthesize.py::synthesize_report_node()` writes `draft_report` and `draft_structured_report`.
- `app/graph/nodes/audit.py::citation_audit()` validates markdown + structured-report consistency.
- `app/graph/nodes/review.py::human_review()` regenerates `final_structured_report` from edited markdown.
- `web/src/types/research.ts` mirrors the backend payload shape.
- `web/src/lib/report.ts` is the frontend boundary for reading and linkifying report payloads.

Structured report validation and error matrix:

| Condition | Validation point | Warning / behavior | Review required |
|-----------|------------------|--------------------|-----------------|
| `draft_report` is empty | `app/graph/nodes/audit.py::citation_audit()` | append `Draft report is empty.` | No by itself; escalates only if another gate also fails |
| findings exist but markdown has no `[S...]` citation | `has_citations(draft_report)` in `citation_audit()` | append `Draft report does not include inline citations.` | Yes in practice, because section-level citation validation also fails |
| markdown references a `source_id` not present in `sources` | `find_missing_citations(draft_report, sources)` | append `Draft report references unknown citations: ...` | Yes |
| structured report has no sections while findings exist | `_validate_structured_report()` in `citation_audit()` | append `Structured report does not include any sections.` | Yes |
| `Executive Summary` exists but has no citation | `_validate_structured_report()` in `citation_audit()` | append `Executive summary does not include inline citations.` | Yes |
| non-background analysis section has content but no citation | `_validate_structured_report()` in `citation_audit()` | append `Section '<heading>' does not include inline citations.` | Yes |
| `cited_source_ids` and `citation_index[*].source_id` diverge | `_validate_structured_report()` in `citation_audit()` | append `Structured report citation index is out of sync with cited sources.` | Yes |

Good / Base / Bad cases for this contract:

- Good:
  `synthesize_report_node()` produces `draft_report` plus `draft_structured_report`, every evidence-bearing section contains `[S...]`, and `citation_index` / `source_cards` reflect the same cited sources.
- Base:
  Human review edits markdown via `edited_report`; `human_review()` accepts the markdown and rebuilds `final_structured_report` with `derive_structured_report()` so the final payload is still structured.
- Bad:
  Markdown includes `"[Sdeadbeef]"` that does not exist in `sources`, or an analysis section omits citations while findings exist; `citation_audit()` must append warnings and set `review_required = True`.

Required tests and assertion points for this contract:

- `tests/unit/test_synthesis.py`
  Assert synthesis output includes `markdown`, `sections`, `citation_index`, and `source_cards`.
- `tests/unit/test_audit.py`
  Assert missing section citations trigger warnings and `review_required = True`.
- `web/src/lib/report.test.ts`
  Assert frontend readers decode structured payloads and linkify inline citations.
- `web/src/components/StructuredReportView.test.tsx`
  Assert the detail UI renders sections, source anchors, and cited source cards from the structured payload.

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
  "tasks": "list of research tasks",
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

#### Worker Task Outcome Contract

```json
{
  "task_id": "string",
  "title": "task title",
  "quality_status": "ok | weak | failed",
  "query_count": "int >= 0",
  "search_hit_count": "int >= 0",
  "acquired_content_count": "int >= 0",
  "kept_source_count": "int >= 0",
  "evidence_count": "int >= 0",
  "host_count": "int >= 0",
  "failure_reasons": "list[str]"
}
```

#### Research Gap Contract

```json
{
  "gap_type": "missing_evidence | weak_evidence | low_source_diversity | retrieval_failure",
  "task_id": "string",
  "title": "short follow-up title",
  "reason": "why the gap exists",
  "retry_hint": "deterministic suggestion for the next planning round",
  "severity": "low | medium | high"
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
  "acquisition_method": "provider_raw_content | http_fetch | search_snippet",
  "metadata": "provider/content metadata used for downstream reasoning"
}
```

#### Environment Contract

```text
LLM_API_KEY              optional, preferred API key for OpenAI-compatible chat endpoints
LLM_BASE_URL             optional, preferred base URL for OpenAI-compatible chat endpoints
OPENAI_API_KEY           optional fallback alias for compatibility
OPENAI_BASE_URL          optional fallback alias for compatibility
TAVILY_API_KEY           optional, enables web search
BRAVE_API_KEY            optional, enables Brave Search aggregation
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
| create conversation API -> manager | validated create payload with explicit `mode` | dispatch to research or chat manager; create conversation, user message, assistant placeholder, and queued run/turn inside the same persistence boundary | return 500 if storage fails before launch |
| generic conversation list/detail API -> store | `conversation_id` optional | return both chat and research conversations with explicit `mode`; research details include `runs`, chat details return an empty `runs` list | return 404 when target conversation is missing |
| follow-up message API -> manager | `conversation_id`, question, optional `parent_run_id` | conversation must exist; conversation `mode` decides whether to call research or chat manager; explicit `parent_run_id` must belong to the same research conversation | return 404 for missing conversation; return 409 when source run is still active, belongs to another conversation, or the mode-specific manager rejects the request |
| follow-up manager -> memory builder | conversation detail, optional persisted conversation memory | build memory from the recent 5 runs; if the requested parent run falls outside the latest 5, force it into the window and recompute older summary on the fly | fall back to deterministic summary rebuild instead of dropping memory context |
| run store -> detail/list API | `run_id` or conversation/list query | run must exist for detail/event routes; conversation must exist for conversation routes | return 404 when target run or conversation is missing |
| ingest_request -> graph state | request payload + memory payload | Normalize integer budgets before Pydantic validation and normalize memory shape into explicit `rolling_summary/recent_turns/key_facts/open_questions` keys | Invalid request values are clamped first, then validated; missing memory fields become empty defaults |
| planner -> tasks | question + gaps + memory | Limit task count to `max_parallel_tasks`; assign iteration-scoped task ids such as `iter-2-task-1`; use memory only as continuity context, never as evidence | Fall back to deterministic task plan with structured gap title/reason/retry-hint when the OpenAI-compatible model path is unavailable |
| task -> worker query rewrite | task question + request scope | Build at most 3 deduplicated queries for a single task | Fall back to deterministic query set without LLM |
| search -> acquire content | provider search hits | Merge duplicate URLs, keep provider metadata, require non-empty URL | Skip invalid hits and tolerate per-provider search failures |
| acquire content -> extract | provider raw content / fetched HTML / snippet fallback | Try provider raw content first, then HTTP fetch, then snippet fallback | Skip unusable content and continue with any surviving acquisition path |
| extract -> evidence scoring | normalized source documents | Drop short or weak pages, choose a focused snippet, and compute bounded `relevance_score` / `confidence` | Skip sources that do not meet the deterministic relevance floor |
| worker -> task outcome | task, queries, ranked hits, acquired contents, kept sources, evidence | derive deterministic quality diagnostics from counts and host diversity | never throw because evidence is weak; emit `quality_status=weak/failed` and failure reasons instead |
| merge -> gap_check | deduplicated findings + `task_outcomes` + current task list | create structured gaps and evaluate quality gate before synthesis | if gate fails and iteration budget remains, replan; if budget is exhausted, continue to synthesis with warnings and force human review |
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
- Planner and synthesizer fall back to deterministic logic while still receiving conversation memory.
- Worker query rewrite, ranking, filtering, and scoring still run deterministically without model access.
- One search provider may be unavailable and the graph still completes from the surviving provider or with an empty-evidence report.
- Legacy string-shaped `gaps` in older run snapshots still degrade to readable open questions in conversation memory.
- Installed `aiosqlite` may omit `Connection.is_alive()` while checkpoint persistence still succeeds through the runtime compatibility shim.
- Browser refreshes during a running job and the frontend restores state via detail API before reopening SSE.
- Conversations with 5 or fewer runs persist an empty `rolling_summary` while still providing explicit recent turns.
- Chat mode may run without model credentials; the chat manager returns a deterministic fallback assistant reply instead of failing the request during initialization.

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
- Unit test deterministic planning fallback when model credentials are absent.
- Unit test `app/services/conversation_memory.py` for recent-5 windowing, parent-run inclusion, digest building, persisted older-summary generation, and structured-gap open-question extraction.
- Unit test `app/run_store.py` for persisted conversation threading, assistant message synchronization, and legacy linkage backfill.
- Unit test `app/run_store.py` for `conversation_memory` read/write behavior.
- Unit test `app/run_manager.py` for async lifecycle transitions, follow-up turn creation, memory injection, and resume rules.
- Unit test deterministic synthesis fallback with conversation memory present and no extra citations.
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
    gaps = identify_research_gaps(tasks, task_outcomes)
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
