# Upgrade langgraph and langchain to 1.0

## Goal
Upgrade the backend from LangChain 0.3 / LangGraph 0.3 to the 1.0 line and update existing code to match the current documented APIs.

## Requirements
- Upgrade `langchain`, `langchain-openai`, `langgraph`, and related checkpoint packages to versions compatible with the 1.0 line.
- Audit all backend usages of LangChain and LangGraph APIs and migrate outdated patterns.
- Keep deterministic fallback behavior when LLM credentials are absent.
- Keep the existing graph/runtime state contracts stable unless a documented dependency change requires an explicit update.
- Update any project docs/spec references that would become inaccurate after the migration.

## Acceptance Criteria
- [ ] Dependency constraints and lockfile target the 1.0-compatible package set.
- [ ] Backend code runs against the upgraded APIs without import/runtime regressions in the touched paths.
- [ ] Lint and Python compilation pass.
- [ ] Relevant tests pass or remaining failures are documented if caused by environment limitations.

## Technical Notes
- Use official LangChain and LangGraph migration documentation as the source of truth.
- Prefer minimal code changes over opportunistic refactors.
