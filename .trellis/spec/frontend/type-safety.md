# Type Safety

> Type safety patterns in this project.

---

## Overview

<!--
Document your project's type safety conventions here.

Questions to answer:
- What type system do you use?
- How are types organized?
- What validation library do you use?
- How do you handle type inference?
-->

(To be filled by the team)

---

## Type Organization

- Mirror backend HTTP and SSE contracts under `web/src/types/`
- Keep component-local props next to the component when they are not shared across routes
- Reuse frontend conversation/run/request/event types instead of re-declaring string unions in components

---

## Validation

- Use `zod` at form boundaries for request payload validation
- Trust backend-validated response payloads after the typed API client boundary

---

## Common Patterns

- Use narrow string unions for run status and event type
- Wrap API envelopes such as `{ run }`, `{ runs }`, and `{ conversation }` in explicit interfaces
- Model thread data as `conversation + messages + runs`; avoid flattening assistant content into ad-hoc component props
- Convert `run.result` access through small helper functions when fields are optional or heterogeneous

---

## Forbidden Patterns

- Do not use `any` for run/event payloads
- Avoid sprinkling `as` assertions into page code; keep casts at the API boundary only when unavoidable
- Do not duplicate backend-only linkage fields such as `conversation_id`, `origin_message_id`, or `assistant_message_id` as local component state
