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

### Services Layer

- Keep services deterministic and side-effect free
- Put merge, dedupe, citation, budget, and synthesis fallback logic here
- Prefer services when logic needs unit tests without external dependencies

### Tools Layer

- Search, fetch, and extraction adapters live here
- Tool code may fail or return partial results; nodes must tolerate that
- Do not hide business decisions inside tools

### Runtime Adapters

- Put async task launch, SSE fan-out, and run persistence adapters in top-level runtime modules such as `app/run_manager.py` and `app/run_store.py`
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
- `app/services/citations.py`: pure validation helper
- `app/tools/fetch.py`: external HTTP boundary
