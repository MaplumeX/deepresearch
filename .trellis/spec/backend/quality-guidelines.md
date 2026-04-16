# Quality Guidelines

> Code quality standards for backend development.

---

## Overview

The backend favors explicit workflow state, pure services, and narrow side-effect boundaries. A change is not considered complete if the control flow is only implied by prompt text or hidden inside a tool implementation.

---

## Forbidden Patterns

### Hidden Orchestration in Tools

Do not put planning, routing, or gap-detection logic inside search/fetch/extract tools.

Why:
- It makes the graph impossible to audit
- It prevents targeted unit tests
- It hides where retries or loops should happen

### Report Generation from Raw Worker Payloads

Do not synthesize directly from `raw_findings` or raw page content.

Why:
- Citations cannot be audited reliably
- Duplicate claims bypass normalization
- The reporting layer becomes coupled to scraping details

---

## Required Patterns

### LLM-Only Entry Contracts

Research and chat entrypoints must reject requests before queueing work when required LLM capabilities are unavailable.

Planning, query rewrite, evidence extraction, heading assignment, synthesis, and chat reply generation must fail explicitly instead of silently degrading to deterministic generated content.

### Pure Service Isolation

Put merge, citation, dedupe, and budget logic in `app/services/` so it can be tested without network calls.

### Explicit State Contract

When changing the graph, update the documented state keys in `research-agent-runtime.md`.

### Repository Lint Entry Point

Run backend lint from the repository root:

```bash
uv run ruff check app tests
```

If the developer is already inside a virtual environment with dev dependencies installed, this is also valid:

```bash
python3 -m ruff check app tests
```

Keep Python lint configuration centralized in the root `pyproject.toml`. Do not add ad-hoc per-directory lint configs unless a tool requires them.

### Behavior-Neutral Cleanup for Tooling Work

When enabling a new static check, prefer the smallest code change that removes the warning without changing runtime behavior.

Examples:
- Remove unused imports instead of weakening the rule
- Build explicit summary objects instead of binding unused placeholder variables
- Avoid blanket ignores such as `# noqa` unless a real false positive is documented

---

## Testing Requirements

- Run `uv run ruff check app tests` for backend changes and Python tooling changes
- Run syntax compilation for `app/` and `tests/`
- Unit test pure service logic first
- Skip provider-dependent tests when the dependency is absent in the current environment
- Add integration tests after the runtime path is stable and provider credentials are available

For Python tooling or quality pipeline changes, the minimum closing check is:

```bash
uv run ruff check app tests
python3 -m compileall app tests
uv run pytest
```

---

## Code Review Checklist

- Do graph nodes only return partial state updates?
- Are side effects isolated to `app/tools/` or runtime adapters?
- Does every inline citation map to a real `source_id`?
- Does the code reject unsupported research/chat requests before queueing work when model readiness is missing?
- Is new reusable logic placed in `app/services/` instead of copied across nodes?
- Does the change keep backend quality tooling discoverable from `pyproject.toml` and documented commands?
