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
POST /api/research/runs/{run_id}/resume
GET /health
```

#### Runtime

```python
async def run_research(request_payload: dict[str, Any], run_id: str) -> dict[str, Any]
async def resume_research(run_id: str, resume_payload: dict[str, Any]) -> dict[str, Any]
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

#### Environment Contract

```text
LLM_API_KEY              optional, preferred API key for OpenAI-compatible chat endpoints
LLM_BASE_URL             optional, preferred base URL for OpenAI-compatible chat endpoints
OPENAI_API_KEY           optional fallback alias for compatibility
OPENAI_BASE_URL          optional fallback alias for compatibility
TAVILY_API_KEY           optional, enables web search
CHECKPOINT_DB_PATH       optional, defaults to research.db
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
| ingest_request -> graph state | request payload | Normalize integer budgets before Pydantic validation | Invalid values are clamped first, then validated |
| planner -> tasks | question + gaps | Limit task count to `max_parallel_tasks` | Fall back to deterministic task plan if the OpenAI-compatible model path is unavailable |
| search -> fetch | search hits | Require non-empty URL before fetch | Skip invalid or failed hits |
| fetch -> extract | HTML/text payload | Extract main text and ignore empty content | Skip empty or failed pages |
| synthesize -> audit | markdown report | Require citations to map to existing `sources` | Set warning and require review when unknown citation ids exist |
| review -> finalize | resume payload | Optional `edited_report` override only | Keep draft report when no edited report is supplied |

### 5. Good/Base/Bad Cases

#### Good
- Request contains a valid question and optional limits.
- Search and fetch produce sources.
- Synthesis emits markdown with valid `[source_id]` citations.
- Audit passes without unknown citations.

#### Base
- No OpenAI-compatible credentials are configured.
- Planner and synthesizer fall back to deterministic logic.
- Search provider may return no results and the graph still completes with an empty-evidence report.

#### Bad
- Empty `question`.
- `max_iterations` or `max_parallel_tasks` outside the accepted range after normalization.
- Report cites a source id that is not present in `sources`.
- Tool fetch fails for all URLs and leaves a task without evidence.

### 6. Tests Required

- Unit test `app/services/citations.py` for citation extraction and missing citation detection.
- Unit test `app/services/dedupe.py` for duplicate-evidence selection.
- Unit test `app/graph/nodes/gap_check.py` for missing-task and corroboration gaps.
- Unit test deterministic planning fallback when model credentials are absent.
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
