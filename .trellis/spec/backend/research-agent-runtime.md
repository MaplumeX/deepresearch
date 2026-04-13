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
GET /health
```

#### Runtime

```python
async def run_research(request_payload: dict[str, Any], run_id: str) -> dict[str, Any]
async def resume_research(run_id: str, resume_payload: dict[str, Any]) -> dict[str, Any]
class ResearchRunManager:
    async def create_run(request_payload: dict[str, Any]) -> ResearchRunDetail
    async def resume_run(run_id: str, resume_payload: dict[str, Any]) -> ResearchRunDetail
    def get_run(run_id: str) -> ResearchRunDetail
    def list_runs() -> list[ResearchRunSummary]
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

#### Run Status Contract

```json
["queued", "running", "interrupted", "completed", "failed"]
```

#### Run Detail Contract

```json
{
  "run_id": "string",
  "status": "queued | running | interrupted | completed | failed",
  "request": "normalized request payload",
  "result": "graph state snapshot or null",
  "warnings": "flattened warnings extracted from result",
  "error_message": "string or null",
  "created_at": "ISO-8601 timestamp",
  "updated_at": "ISO-8601 timestamp",
  "completed_at": "ISO-8601 timestamp or null"
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
    "run": "optional run detail snapshot"
  }
}
```

#### Graph State Contract

```json
{
  "request": "normalized request payload",
  "tasks": "list of research tasks",
  "raw_findings": "append-only list of worker evidence",
  "raw_source_batches": "append-only list of worker source maps",
  "findings": "deduplicated evidence list",
  "sources": "source_id -> source document",
  "gaps": "list of follow-up research gaps",
  "warnings": "report validation warnings",
  "draft_report": "markdown draft",
  "final_report": "final markdown output",
  "iteration_count": "completed planning rounds",
  "review_required": "whether interrupt-based review is required"
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
| create API -> run store | validated request payload | persist queued run before background task launch | return 500 if storage fails before launch |
| run store -> detail/list API | `run_id` or list query | run must exist for detail/event routes | return 404 when run is missing |
| ingest_request -> graph state | request payload | Normalize integer budgets before Pydantic validation | Invalid values are clamped first, then validated |
| planner -> tasks | question + gaps | Limit task count to `max_parallel_tasks` | Fall back to deterministic task plan if the OpenAI-compatible model path is unavailable |
| task -> worker query rewrite | task question + request scope | Build at most 3 deduplicated queries for a single task | Fall back to deterministic query set without LLM |
| search -> acquire content | provider search hits | Merge duplicate URLs, keep provider metadata, require non-empty URL | Skip invalid hits and tolerate per-provider search failures |
| acquire content -> extract | provider raw content / fetched HTML / snippet fallback | Try provider raw content first, then HTTP fetch, then snippet fallback | Skip unusable content and continue with any surviving acquisition path |
| extract -> evidence scoring | normalized source documents | Drop short or weak pages, choose a focused snippet, and compute bounded `relevance_score` / `confidence` | Skip sources that do not meet the deterministic relevance floor |
| synthesize -> audit | markdown report | Require citations to map to existing `sources` | Set warning and require review when unknown citation ids exist |
| review -> finalize | resume payload | Optional `edited_report` override only | Keep draft report when no edited report is supplied |
| resume API -> runtime | `approved`, optional `edited_report` | run must be in `interrupted` status before resume | return 409 if client resumes a non-interrupted run |
| SSE endpoint -> frontend | `run_id` event stream | run must exist and payload must stay JSON-safe | send keep-alive comments while waiting; close after terminal states |

### 5. Good/Base/Bad Cases

#### Good
- Request contains a valid question and optional limits.
- Create API returns queued run immediately.
- Query rewrite produces focused task queries.
- Tavily and Brave can both contribute hits for the same worker task.
- Provider raw content is used when available; HTTP fetch and snippet fallback cover the rest.
- Evidence scoring keeps only relevant sources and emits bounded scores.
- Synthesis emits markdown with valid `[source_id]` citations.
- Audit passes without unknown citations.
- Detail API and SSE stream both reflect the same terminal snapshot.

#### Base
- No OpenAI-compatible credentials are configured.
- Planner and synthesizer fall back to deterministic logic.
- Worker query rewrite, ranking, filtering, and scoring still run deterministically without model access.
- Search provider may return no results and the graph still completes with an empty-evidence report.
- Browser refreshes during a running job and the frontend restores state via detail API before reopening SSE.

#### Bad
- Empty `question`.
- `max_iterations` or `max_parallel_tasks` outside the accepted range after normalization.
- Report cites a source id that is not present in `sources`.
- Both providers fail or return unusable hits for all queries.
- Provider raw content, HTTP fetch, and snippet fallback all fail or stay too weak for evidence extraction.
- Client attempts to resume a completed run.
- Server restarts while queued/running jobs exist and leaves stale statuses unmarked.

### 6. Tests Required

- Unit test `app/services/citations.py` for citation extraction and missing citation detection.
- Unit test `app/services/dedupe.py` for duplicate-evidence selection.
- Unit test `app/services/research_worker.py` for query rewrite, cross-provider search-hit ranking, content filtering, and evidence scoring.
- Unit test `app/tools/extract.py` for provider-aware content normalization.
- Unit test `app/graph/nodes/gap_check.py` for missing-task and corroboration gaps.
- Unit test deterministic planning fallback when model credentials are absent.
- Unit test `app/run_store.py` for persisted run snapshots.
- Unit test `app/run_manager.py` for async lifecycle transitions and resume rules.
- Syntax compilation for `app/` and `tests/`.

### 7. Wrong vs Correct

#### Wrong

```python
def synthesize_report_node(state: dict) -> dict:
    report = llm.invoke(state["raw_findings"])
    return {"draft_report": report}
```

- Problem: raw worker payload is consumed directly, citations are not normalized, and fallback behavior is missing.

#### Correct

```python
def synthesize_report_node(state: dict) -> dict:
    report = synthesize_report(
        question=state["request"]["question"],
        tasks=state.get("tasks", []),
        findings=state.get("findings", []),
        sources=state.get("sources", {}),
        settings=get_settings(),
    )
    return {"draft_report": report.markdown}
```

- Reason: the node consumes normalized state, preserves citation boundaries, and supports deterministic fallback.
