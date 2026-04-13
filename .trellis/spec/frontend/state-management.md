# State Management

> How state is managed in this project.

---

## Overview

<!--
Document your project's state management conventions here.

Questions to answer:
- What state management solution do you use?
- How is local vs global state decided?
- How do you handle server state?
- What are the patterns for derived state?
-->

(To be filled by the team)

---

## State Categories

- Local state: transient form edits and UI-only event logs
- URL state: route params such as `runId`
- Server state: run list, run detail, and resume/create mutations
- Realtime state: SSE events merged into React Query caches

---

## When to Use Global State

- Prefer React Query cache for data fetched from the backend
- Promote to explicit global state only when multiple distant routes need non-server UI state
- Do not build a second client-side store for run detail if React Query + SSE already own it

---

## Server State

- Use TanStack Query for list/detail queries and create/resume mutations
- Let SSE patch list/detail caches in place so the UI does not need polling
- Close realtime subscriptions when a run reaches `completed` or `failed`

---

## Common Mistakes

- Duplicating backend status strings inside multiple components instead of importing shared types
- Mixing SSE-updated detail state with a separate local copy that silently drifts
