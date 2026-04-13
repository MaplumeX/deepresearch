# Build Python Deep Research Agent Scaffold

## Goal
Build a minimal but extensible Python backend scaffold for a deep research agent using LangGraph as the orchestration layer and LangChain as the model/tool integration layer.

## Requirements
- Create a Python project scaffold with dependency metadata.
- Add a backend package layout for domain models, graph state, nodes, tools, services, and API routes.
- Implement a LangGraph main graph with planning, dispatch, research, merge, gap check, synthesis, audit, review, and finalize stages.
- Implement a research worker subgraph entry point that can later be replaced or wrapped by Deep Agents.
- Add a FastAPI entry point for running a research request and resuming interrupted runs.
- Use deterministic fallbacks for planning and synthesis when LLM credentials are not configured.
- Keep the first version focused on single-run research with SQLite checkpoint persistence.
- Add minimal tests for pure business logic that do not depend on external services.

## Acceptance Criteria
- [ ] `pyproject.toml` exists with the initial backend dependencies.
- [ ] The repository contains a runnable Python package structure under `app/`.
- [ ] The graph builder composes the planned research workflow with explicit state and routing.
- [ ] API schemas and routes exist for starting and resuming a run.
- [ ] Pure service logic has unit tests.
- [ ] The codebase passes at least syntax compilation in the current environment.

## Technical Notes
- Backend-only scope for this task. No frontend work.
- State contract:
  - `request`
  - `tasks`
  - `raw_findings`
  - `raw_source_batches`
  - `findings`
  - `sources`
  - `gaps`
  - `warnings`
  - `draft_report`
  - `final_report`
  - `iteration_count`
  - `review_required`
- API contract:
  - `POST /api/research/runs` accepts a research request and returns a run id plus current result.
  - `POST /api/research/runs/{run_id}/resume` accepts a resume payload and continues an interrupted run.
- Validation and error matrix:
  - Good: valid question and optional limits produce a normalized request and run result.
  - Base: missing optional config uses deterministic fallback planner/synthesizer.
  - Bad: empty question or invalid limits raise validation errors before graph execution.
