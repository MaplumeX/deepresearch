# Directory Structure

> How backend code is organized in this project.

---

## Overview

The backend is organized by responsibility, not by framework artifact type alone:

- `app/api/` exposes FastAPI schemas and routes
- `app/domain/` defines stable business models
- `app/graph/` owns LangGraph state, nodes, routing, and worker entry points
- `app/services/` holds pure business logic with no network side effects
- `app/tools/` handles external I/O such as search, fetch, and extraction
- `app/runtime.py` wires checkpoint persistence and graph execution
- `app/run_store.py` persists run snapshots and history
- `app/run_manager.py` owns async run lifecycle, background tasks, and SSE fan-out
- `app/cli.py` exposes the backend startup entrypoint for local development and runtime launch

This keeps orchestration logic explicit while avoiding tool code leaking into graph nodes.

---

## Directory Layout

```text
app/
├── api/
│   ├── routes.py
│   └── schemas.py
├── domain/
│   └── models.py
├── graph/
│   ├── builder.py
│   ├── state.py
│   ├── nodes/
│   └── subgraphs/
├── services/
├── tools/
├── cli.py
├── run_manager.py
├── run_store.py
├── config.py
├── main.py
└── runtime.py
tests/
└── unit/
```

---

## Module Organization

### Graph Layer

- One file per node under `app/graph/nodes/`
- Node files should only read state, call services/tools, and return partial state updates
- Routing helpers belong next to the node they support when the logic is local
- Use `app/graph/subgraphs/` when one workflow stage needs multiple internal steps but the outer graph contract should stay stable
- Subgraph entry points should still expose a narrow state interface to the outer graph, for example task-level `request` + `task` in and reducer-friendly payloads out

### Services Layer

- Keep services deterministic and side-effect free
- Put merge, dedupe, citation, budget, prompt compaction, and LLM output validation logic here
- Prefer services when logic needs unit tests without external dependencies
- Put ranking, filtering, scoring, and snippet-selection logic here when a worker needs business decisions without network side effects

### Tools Layer

- Search, fetch, and extraction adapters live here
- Tool code may fail or return partial results; nodes must tolerate that
- Do not hide business decisions inside tools
- Extraction tools should normalize raw payloads into source documents, while claim generation and evidence scoring stay in `app/services/`

### Runtime Adapters

- Put async task launch, SSE fan-out, and run persistence adapters in top-level runtime modules such as `app/run_manager.py` and `app/run_store.py`
- Keep backend startup wiring in a top-level runtime module such as `app/cli.py`; do not bury process launch or env bootstrap logic inside API routes, services, or graph nodes
- Keep these modules thin: they orchestrate infrastructure boundaries but should not duplicate graph logic or business rules from `app/services/`

---

## Naming Conventions

- Use snake_case file names
- Name nodes by workflow stage, for example `planner.py`, `merge.py`, `audit.py`
- Name pure helpers by domain action, for example `dedupe.py`, `citations.py`
- Keep one top-level package root: `app/`

---

## Examples

- `app/graph/builder.py`: main workflow assembly
- `app/graph/subgraphs/research_worker.py`: worker execution boundary
- `app/services/research_worker.py`: deterministic ranking, filtering, and evidence scoring for worker stages
- `app/services/citations.py`: pure validation helper
- `app/tools/fetch.py`: external HTTP boundary
