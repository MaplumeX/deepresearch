# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a deep research agent built on **LangGraph + LangChain** (Python backend) and **React + Vite** (frontend). It performs multi-step research workflows: planning, task dispatch, parallel research worker execution, evidence merging, gap checking, synthesis, citation audit, and optional human review.

## Common Commands

### Backend

Run the API server:
```bash
uv run deepresearch-api
# Optional: --host 0.0.0.0 --port 9000 --no-reload
```

Lint:
```bash
uv run ruff check app tests
```

Type/syntax checks:
```bash
python3 -m compileall app tests
```

Tests:
```bash
uv run pytest
```

### Frontend

```bash
cd web
npm install
npm run dev      # Start dev server (proxies /api to backend)
npm run lint
npm run typecheck
npm run build
```

## High-Level Architecture

### Backend (`app/`)

- **`app/api/routes.py`** — FastAPI router. Exposes `/health`, `/api/research/runs`, `/api/conversations`, and SSE event streams (`/events`).
- **`app/main.py`** — FastAPI app factory. Wires `ResearchRunManager`, `ChatConversationManager`, and `ResearchRunStore` into `app.state`.
- **`app/run_manager.py`** — Orchestrates research runs via `run_research()` / `resume_research()` from `app/runtime.py`, and streams progress/events.
- **`app/runtime.py`** — Graph runner. Builds initial state, invokes the compiled LangGraph, and reads snapshots. Uses `AsyncSqliteSaver` for checkpointing.
- **`app/graph/builder.py`** — Defines the LangGraph node graph and conditional edges.
- **`app/graph/state.py`** — `GraphState` (TypedDict). Shared state across all graph nodes.
- **`app/graph/nodes/`** — Graph node implementations. Each node receives state and returns a partial state update.
- **`app/graph/subgraphs/research_worker.py`** — Subgraph executed per research task (search, fetch, extract).
- **`app/services/`** — Pure business logic: planning, synthesis, dedupe, citations, budgets, evidence extraction, conversation memory, etc. Keep logic here so it can be unit-tested without network calls.
- **`app/tools/`** — Side-effect boundaries: `search.py`, `fetch.py`, `extract.py`. All external I/O lives here.
- **`app/run_store.py`** — SQLite-backed run and conversation persistence.
- **`app/config.py`** — Settings loaded from `.env` (e.g., `LLM_BASE_URL`, `PLANNER_MODEL`, `TAVILY_API_KEY`).

Graph flow:
```
ingest_request → clarify_scope → plan_research → emit_plan_message → plan_review
                                                          ↑___________↓
                                                          (plan_chat loop)
dispatch_tasks → research_worker → merge_evidence → gap_check → synthesize_report
→ citation_audit → human_review → finalize
```

### Frontend (`web/src/`)

- **`App.tsx`** — Root component.
- **`layouts/MainLayout.tsx`** — Main UI shell with sidebar and chat area.
- **`components/`** — React components: `ChatArea`, `ChatInput`, `ResearchProgressCard`, `ConversationList`, etc.
- **`store/`** — Zustand stores: `useChatStore`, `useSettingsStore`, `useUiStore`.
- **`lib/api.ts`** — API client functions.
- **`lib/research-progress.ts`** / **`lib/research-result.ts`** — Research-specific parsing/helpers.
- **`types/research.ts`** — TypeScript domain types.

## Development Standards (from `.trellis/spec/`)

**CRITICAL: Before writing code, read the relevant `.trellis/spec/` guidelines.**

- Backend deep research: read `.trellis/spec/backend/quality-guidelines.md` and `.trellis/spec/backend/research-agent-runtime.md`.
- Frontend work: read `.trellis/spec/frontend/quality-guidelines.md`.
- Cross-layer features: read `.trellis/spec/guides/cross-layer-thinking-guide.md`.

### Backend Quality Rules

- **State changes stay inside graph nodes**; pure logic stays in `app/services/`.
- **External side effects stay inside `app/tools/`** or runtime adapters.
- **Research and chat entrypoints must reject unsupported requests before queueing work when LLM readiness is missing.**
- **Reports must only cite `source_id`s that exist in `sources`.**
- Add unit coverage for pure service logic.

### Frontend Quality Rules

- Frontend quality tooling is owned locally in `web/`: `npm run lint`, `npm run typecheck`, `npm run build`.
- Keep config in `web/eslint.config.js` and `web/package.json`.
- Avoid `eslint-disable` or `@ts-ignore` unless there is a documented false positive.

### Workflow Rules

- Use the Trellis task system: `python3 ./.trellis/scripts/task.py list` / `create`.
- **Do not execute `git commit`.** The human commits after testing.
- After committing, record the session: `python3 ./.trellis/scripts/add_session.py --title "..." --commit <hash>`.
- Use `/trellis:finish-work` for the pre-commit checklist.
