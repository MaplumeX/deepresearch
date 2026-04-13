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

### Deterministic Fallbacks

When LLM credentials are missing, planning and synthesis must still complete with deterministic fallback behavior.

### Pure Service Isolation

Put merge, citation, dedupe, and budget logic in `app/services/` so it can be tested without network calls.

### Explicit State Contract

When changing the graph, update the documented state keys in `research-agent-runtime.md`.

---

## Testing Requirements

- Run syntax compilation for `app/` and `tests/`
- Unit test pure service logic first
- Skip provider-dependent tests when the dependency is absent in the current environment
- Add integration tests after the runtime path is stable and provider credentials are available

---

## Code Review Checklist

- Do graph nodes only return partial state updates?
- Are side effects isolated to `app/tools/` or runtime adapters?
- Does every inline citation map to a real `source_id`?
- Does the code still work without model credentials?
- Is new reusable logic placed in `app/services/` instead of copied across nodes?
