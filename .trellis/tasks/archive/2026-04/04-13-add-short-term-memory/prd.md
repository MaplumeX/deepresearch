# Add Short-Term Conversation Memory

## Goal
Add backend short-term memory for research conversations so follow-up runs can use the latest conversation context without changing the public API contract.

## Requirements
- Keep the existing conversation, run, and checkpoint architecture intact.
- Use the most recent 5 runs in a conversation as the explicit short-term memory window.
- Treat one run as one turn: one user message and one assistant message.
- Persist compressed memory for turns outside the recent 5-run window.
- Build memory on the server side when creating a follow-up message.
- Inject memory into graph state so planning and synthesis can consume it.
- Keep memory as background context only, not as a citation source.
- Leave resume flow behavior unchanged.
- Add deterministic fallback logic so memory works without LLM credentials.

## Acceptance Criteria
- [ ] A new follow-up run receives a memory payload built from the recent 5 runs plus persisted summary of older runs.
- [ ] New conversations still run correctly with empty memory.
- [ ] Resume flow still relies only on checkpoint state and passes existing behavior.
- [ ] Planner and synthesis consume memory without treating it as evidence or citations.
- [ ] Unit tests cover memory windowing, parent inclusion, persistence, and runtime integration.
- [ ] Runtime/spec docs describe the new memory contract and persistence.

## Technical Notes
- Backend-only change with test and documentation updates.
- Add a dedicated memory service in `app/services/`.
- Add minimal persistence for conversation memory in `app/run_store.py`.
- Extend graph state contract explicitly in docs and code.
