# Journal - codex-agent (Part 1)

> AI development session journal
> Started: 2026-04-13

---



## Session 1: Fix editable install and planning test drift

**Date**: 2026-04-13
**Task**: Fix editable install and planning test drift
**Branch**: `master`

### Summary

(Add summary)

### Main Changes

| Item | Description |
|------|-------------|
| Packaging fix | Added explicit Hatch wheel package selection for the `app` package root so `pip install -e ".[dev]"` can build editable metadata successfully. |
| Dependency cleanup | Removed the unused `deepagents` dependency because its current `langgraph` requirement conflicts with this scaffold's pinned `langgraph` range. |
| Test repair | Updated the planning unit test to use the current `Settings` fields `llm_api_key` and `llm_base_url`. |
| Verification | Re-ran editable install, `python -m compileall app tests`, and `python -m unittest discover -s tests/unit`; all passed. |

**Updated Files**:
- `pyproject.toml`
- `tests/unit/test_planning.py`

**Archived Tasks**:
- `04-13-fix-editable-install-packaging`
- `04-13-fix-planning-tests-settings-rename`


### Git Commits

| Hash | Message |
|------|---------|
| `89ddc7e` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 2: Document current LangGraph graph

**Date**: 2026-04-13
**Task**: Document current LangGraph graph
**Branch**: `master`

### Summary

(Add summary)

### Main Changes

| Item | Description |
|------|-------------|
| Output | Added a current-state LangGraph analysis document under `docs/current-langgraph-graph.md` |
| Scope | Mapped the graph builder, state contract, nodes, routing, interrupt/resume flow, runtime, run manager, store, and API entry points |
| Task | Archived completed task `04-13-analyze-langgraph-graph` after the work commit |

**Updated Files**:
- `docs/current-langgraph-graph.md`
- `.trellis/tasks/archive/2026-04/04-13-analyze-langgraph-graph/task.json`
- `.trellis/workspace/codex-agent/journal-1.md`


### Git Commits

| Hash | Message |
|------|---------|
| `3b432de` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 3: Build async research workspace and web app

**Date**: 2026-04-13
**Task**: Build async research workspace and web app
**Branch**: `master`

### Summary

Added an async run lifecycle with persisted history and SSE, plus a new React web workspace for creating, browsing, and reviewing deep research runs.

### Main Changes

| Item | Description |
|------|-------------|
| Backend lifecycle | Added persisted async run management with list/detail APIs, resume handling, and SSE event streaming. |
| Frontend workspace | Added a new `web/` React + TypeScript app with create page, history page, detail page, and review flow. |
| Contracts | Synced backend/frontend run status, event payloads, environment variables, and docs/specs for the new async workflow. |
| Verification | Re-ran Python unit tests, frontend typecheck, Vitest, and production build before recording the session. |

**Updated Files**:
- `app/api/routes.py`
- `app/api/schemas.py`
- `app/config.py`
- `app/domain/models.py`
- `app/main.py`
- `app/runtime.py`
- `app/run_manager.py`
- `app/run_store.py`
- `tests/unit/test_run_manager.py`
- `tests/unit/test_run_store.py`
- `web/`
- `.trellis/spec/backend/research-agent-runtime.md`
- `.trellis/spec/frontend/directory-structure.md`
- `.trellis/spec/frontend/state-management.md`
- `.trellis/spec/frontend/type-safety.md`
- `README.md`

**Archived Tasks**:
- `04-13-deep-research-frontend`

### Git Commits

| Hash | Message |
|------|---------|
| `2528cff` | (see git log) |

### Testing

- [OK] `python3 -m compileall app tests`
- [OK] `python3 -m unittest discover -s tests/unit`
- [OK] `cd web && npm run typecheck`
- [OK] `cd web && npm run test`
- [OK] `cd web && npm run build`

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 4: 重构 ChatGPT 风格研究工作台 UI

**Date**: 2026-04-13
**Task**: 重构 ChatGPT 风格研究工作台 UI
**Branch**: `master`

### Summary

将前端重构为工作台式布局：左侧历史侧栏、composer 首页、统一的 run 详情工作区，并补充历史列表组件测试。

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `a06c50b` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 5: Upgrade research_worker to staged subgraph

**Date**: 2026-04-13
**Task**: Upgrade research_worker to staged subgraph
**Branch**: `master`

### Summary

Refactored research_worker into an internal staged subgraph, extracted deterministic query ranking/filtering/scoring logic into app/services/research_worker.py, narrowed extract tool responsibilities, updated backend runtime/docs specs, and verified with unit tests plus compileall.

### Main Changes

(Add details)

### Git Commits

| Hash | Message |
|------|---------|
| `69196c4` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete


## Session 6: Improve multi-provider web search pipeline

**Date**: 2026-04-13
**Task**: Improve multi-provider web search pipeline
**Branch**: `master`

### Summary

(Add summary)

### Main Changes

| Area | Description |
|------|-------------|
| Search | Added Tavily + Brave multi-provider aggregation for research worker search. |
| Content pipeline | Reworked retrieval to use provider raw content, HTTP fetch fallback, and snippet fallback. |
| Models | Extended backend search/source models with provider metadata and acquisition method fields. |
| Ranking | Added cross-provider merge, host diversity handling, and acquisition-aware scoring. |
| Verification | Added provider-aware extract tests and updated research-worker tests and runtime docs. |

**Updated Files**:
- `app/config.py`
- `app/domain/models.py`
- `app/tools/search.py`
- `app/tools/fetch.py`
- `app/tools/extract.py`
- `app/services/research_worker.py`
- `app/graph/subgraphs/research_worker.py`
- `tests/unit/test_research_worker_service.py`
- `tests/unit/test_extract_tool.py`
- `.trellis/spec/backend/research-agent-runtime.md`
- `README.md`
- `docs/current-langgraph-graph.md`


### Git Commits

| Hash | Message |
|------|---------|
| `ddeb196` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete
