# brainstorm: upgrade deep research event stream display

## Goal

Upgrade the deep research live event display so users can understand what the system is doing while a research run is in progress, instead of only seeing a generic loading state and then a final report.

## What I already know

* The current frontend uses a single `useChatStore` Zustand store to manage conversations, SSE subscriptions, and the active streaming preview.
* `ChatArea` currently renders research progress as either a generic typing indicator or a markdown preview from `streamingAssistantPreview`.
* The frontend subscribes to research SSE events through `/api/research/runs/{run_id}/events`.
* Research-mode SSE events are typed only as a generic `SSEEvent`, and the UI does not currently model a structured event timeline.
* The current backend emits `run.created`, `run.status_changed`, `run.progress`, `run.interrupted`, `run.completed`, `run.failed`, and `run.resumed`.
* For research runs, `run.progress` currently carries only coarse text messages like `Research execution started.` and `Review submitted. Resuming research.`
* Research assistant message content is not token-streamed during execution. It is written when the run is completed, interrupted, or failed.
* Historical brainstorm work in this repo already pointed toward rendering assistant progress blocks inline in the thread, not only final report content.

## Assumptions (temporary)

* This task is primarily a frontend UX upgrade first, with backend contract changes only if needed to unlock higher-fidelity progress display.
* The desired outcome is to make research progress feel visible and trustworthy, not to simulate token streaming when the backend does not provide it.
* Keeping the current conversation-first workspace is preferable to reintroducing a separate run dashboard.

## Open Questions

* None currently blocking.

## Requirements (evolving)

* Show research execution progress as a real event stream, not only a spinner.
* Keep the final report display in the same conversation thread.
* Preserve the current single-stream subscription model in `useChatStore`.
* Avoid misleading fake token streaming for research results.
* Keep the UI readable on both desktop and mobile.
* Support static replay when reopening a completed research conversation later.

## Acceptance Criteria (evolving)

* [ ] A user can see distinct research progress states while a run is active.
* [ ] The active run display distinguishes process updates from the final answer.
* [ ] The design fits the existing conversation-first workspace.
* [ ] The chosen scope is explicit about whether backend SSE contracts change.

## Definition of Done (team quality bar)

* The chosen event-stream display direction is implemented without regressing existing chat or research flows.
* Frontend lint and typecheck pass.
* Any changed SSE/event contracts are mirrored in `web/src/types/research.ts`.
* Spec docs are updated if backend or cross-layer contracts change.

## Out of Scope (explicit)

* Rewriting the entire research runtime.
* A speculative full observability platform or admin console.
* Simulated token streaming of final report text without real backend support.

## Technical Notes

* Relevant files inspected:
  * `web/src/components/ChatArea.tsx`
  * `web/src/components/ChatInput.tsx`
  * `web/src/components/Sidebar.tsx`
  * `web/src/store/useChatStore.ts`
  * `web/src/lib/api.ts`
  * `web/src/types/research.ts`
  * `app/run_manager.py`
  * `app/run_store.py`
  * `.trellis/spec/frontend/state-management.md`
  * `.trellis/spec/frontend/quality-guidelines.md`
  * `.trellis/spec/frontend/directory-structure.md`
  * `.trellis/spec/frontend/type-safety.md`
  * `.trellis/spec/backend/research-agent-runtime.md`
  * `.trellis/tasks/archive/2026-04/04-13-chatgpt-like-ui-rebuild/prd.md`

## Research Notes

### Current product reality

* Research mode is process-driven, not token-stream-driven.
* The backend already has an SSE channel, but the payload is too coarse for rich process visualization.
* The frontend already has the right shell for an inline thread-native progress block.

### Feasible approaches here

**Approach A: Frontend-only event timeline**

* Derive a lightweight timeline from existing `type`, `status`, and `data.message`.
* Show created/running/completed/failed/interrupted milestones plus message rows.
* Lowest scope and lowest risk.
* Limited by coarse backend event detail.

**Approach B: Thread-native progress card with inferred stages** (Likely best MVP)

* Keep current backend contract.
* Introduce a dedicated in-thread research-progress block that maps current events into a small set of UX stages such as queued, researching, waiting-review, finished, failed.
* Separate process UI from final markdown report.
* Better user experience than a raw log, but still partly heuristic.

**Approach C: Structured progress protocol**

* Extend backend SSE events with explicit phase/task metadata such as stage key, stage label, task counts, source counts, or current worker activity.
* Frontend renders a richer timeline, expandable detail rows, and more accurate progress indicators.
* Highest product ceiling and cleanest long-term model.
* Requires cross-layer contract work and spec updates.

## Decision

Implement **Approach B + C together**:

* Frontend renders a thread-native `ResearchProgressCard` instead of reusing the markdown preview area as pseudo-streaming output.
* Backend extends the research SSE payload with structured progress metadata so the frontend does not have to infer every stage heuristically from raw strings.

## Detailed Design

### Product behavior

For an active research run, the assistant area should be split into two different concepts:

* **Process block**: a live progress card that explains what the system is doing now.
* **Answer block**: the final assistant report markdown shown only when the run reaches `completed` or `interrupted`.

The UI should stop pretending that research mode streams report tokens. Instead:

* While the run is `queued` or `running`, show a progress card in the thread.
* When the run finishes, replace the live state with a completed summary state and then show the final markdown report as the assistant message.
* When the run is interrupted for review, keep the progress card visible in an `awaiting_review` state and show any draft report content below it if available.
* For failed runs, show the progress card in a failed state and keep the assistant failure text as the assistant message.

For historical conversations:

* Reopening a conversation should still show each research run's progress card in its final historical form.
* Historical replay is **static**, not animated.
* Users should be able to expand a historical event log and inspect the stages/tasks the run went through.
* Historical replay should render from persisted event history, not by inferring process state back out of the final report.

### UX shape

The `ResearchProgressCard` should include:

* stage label, short description, and status chip
* elapsed / timestamp hint
* compact progress stepper for top-level stages
* current task title when inside task execution
* optional metrics row:
  * planned tasks
  * completed tasks
  * evidence count
  * source count
  * iteration number
* expandable event log for low-level details

The card should stay visually lighter than the final markdown response so users can scan process state without confusing it with the answer itself.

### Top-level research stages

The structured protocol should normalize runtime activity into a small stable stage set:

* `queued`
* `clarifying_scope`
* `planning`
* `executing_tasks`
* `merging_evidence`
* `checking_gaps`
* `replanning`
* `synthesizing`
* `auditing`
* `awaiting_review`
* `finalizing`
* `completed`
* `failed`

`replanning` is represented explicitly because the graph can loop from `gap_check` back to `plan_research`.

### Task sub-stages

When the stage is `executing_tasks`, the current task may also report a nested worker step:

* `rewrite_queries`
* `search_and_rank`
* `acquire_and_filter`
* `extract_and_score`
* `emit_results`

This gives the frontend enough fidelity to say "正在检索来源" vs "正在提取证据".

### Backend event contract change

Keep existing event names for compatibility:

* `run.created`
* `run.status_changed`
* `run.progress`
* `run.interrupted`
* `run.completed`
* `run.failed`
* `run.resumed`

Extend the `data` payload with a structured `progress` object on research events.

Proposed contract:

```json
{
  "type": "run.progress",
  "run_id": "string",
  "status": "queued | running | interrupted | completed | failed",
  "timestamp": "ISO-8601 timestamp",
  "data": {
    "message": "optional human-readable summary",
    "run": "optional run detail snapshot",
    "conversation": "optional conversation summary snapshot",
    "assistant_message": "optional assistant message snapshot",
    "progress": {
      "phase": "queued | clarifying_scope | planning | executing_tasks | merging_evidence | checking_gaps | replanning | synthesizing | auditing | awaiting_review | finalizing | completed | failed",
      "phase_label": "localized display label",
      "iteration": 1,
      "max_iterations": 2,
      "task": {
        "task_id": "iter-1-task-1",
        "title": "Investigate ...",
        "index": 1,
        "total": 3,
        "status": "pending | running | done | failed",
        "worker_step": "rewrite_queries | search_and_rank | acquire_and_filter | extract_and_score | emit_results | null"
      },
      "counts": {
        "planned_tasks": 3,
        "completed_tasks": 1,
        "search_hits": 8,
        "acquired_contents": 3,
        "kept_sources": 2,
        "evidence_count": 4,
        "warnings": 1
      },
      "review": {
        "required": false,
        "kind": "human_review | null"
      }
    }
  }
}
```

Design constraints:

* `message` remains optional for backward compatibility and fallback rendering.
* `progress` is additive, not replacing `run`, `conversation`, or `assistant_message`.
* Terminal events should also carry the final `progress.phase` (`completed`, `awaiting_review`, or `failed`) so the frontend can close the stream cleanly without losing the last visible state.

### Event persistence for static replay

Static replay requires durable event history. The current `research_runs.result_json` is not enough because it stores only the final graph snapshot.

Add a dedicated persistence table for research run events, for example:

```text
research_run_events(
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  sequence_no INTEGER NOT NULL,
  event_type TEXT NOT NULL,
  status TEXT NOT NULL,
  timestamp TEXT NOT NULL,
  message TEXT,
  progress_json TEXT NOT NULL
)
```

Recommended storage rules:

* Persist every meaningful research event:
  * `run.created`
  * `run.status_changed`
  * `run.progress`
  * `run.resumed`
  * `run.interrupted`
  * `run.completed`
  * `run.failed`
* Do **not** persist keep-alive comments.
* Persist a normalized progress payload, not full duplicated `run` / `conversation` / `assistant_message` snapshots for every row.
* `sequence_no` must be monotonic per run so replay order is deterministic even if timestamps are equal.

### Read model for historical replay

Static replay should be available directly from conversation detail fetches. The frontend thread renderer already consumes `conversation.messages` plus `conversation.runs`, so the most compatible extension is:

* Add `progress_events` to `ResearchRunDetail`.

Proposed detail shape:

```json
{
  "run_id": "string",
  "status": "completed",
  "progress_events": [
    {
      "event_type": "run.progress",
      "status": "running",
      "timestamp": "ISO-8601",
      "message": "Planning research tasks.",
      "progress": { "...": "normalized progress payload" }
    }
  ]
}
```

Why this shape is preferred here:

* `ChatArea` already renders the thread from `conversation.messages` and can place each run's progress card next to its assistant message using `message.run_id`.
* Opening one conversation yields everything needed for static replay in one request.
* It avoids opening N separate SSE/history connections when a conversation contains N runs.

Trade-off:

* `GET /api/conversations/{conversation_id}` payloads become larger.

For the current product scope, this is acceptable because:

* runs per conversation are still limited in practice
* per-run event count is small if we emit only meaningful orchestration boundaries
* it keeps frontend architecture simpler than introducing a second history-fetch path

### Backend emission strategy

Emit structured progress from stable orchestration boundaries, not from arbitrary utility functions.

Recommended emission points:

* `ResearchRunManager._create_turn()`:
  * publish `run.created` with `phase=queued`
* `ResearchRunManager._execute_run()`:
  * publish `run.status_changed` with `phase=queued`
  * publish `run.progress` with `phase=clarifying_scope`
* `clarify_scope`
  * emit `phase=clarifying_scope`
* `plan_research`
  * emit `phase=planning` with task totals and iteration number
* `dispatch_tasks`
  * emit `phase=executing_tasks` with planned task totals
* `research_worker` subgraph:
  * emit `phase=executing_tasks` plus task metadata and `worker_step`
* `merge_evidence`
  * emit `phase=merging_evidence` with aggregated source/evidence counts
* `gap_check`
  * emit `phase=checking_gaps` with warning/gap counts
* `after_gap_check -> plan_research`
  * emit `phase=replanning`
* `synthesize_report`
  * emit `phase=synthesizing`
* `citation_audit`
  * emit `phase=auditing`
* `human_review`
  * emit `phase=awaiting_review`, `review.required=true`
* `finalize`
  * emit `phase=finalizing`
* terminal manager publish:
  * `run.completed` with `phase=completed`
  * `run.interrupted` with `phase=awaiting_review`
  * `run.failed` with `phase=failed`

Implementation note:

* The cleanest approach is to pass a progress callback through `run_research()` / `resume_research()` into graph nodes and the worker subgraph, instead of teaching the frontend to reverse-engineer graph state snapshots.
* The same callback should both publish live SSE events and persist normalized history rows so live rendering and static replay come from one source of truth.

### Backend store changes

`ResearchRunStore` needs:

* table initialization for `research_run_events`
* append API such as `append_run_event(run_id, event)`
* query API such as `list_run_events(run_id) -> list[ResearchRunHistoryEvent]`
* conversation deletion must also delete `research_run_events` rows for that conversation's runs
* `get_run()` / `get_conversation()` should hydrate `progress_events` onto `ResearchRunDetail`

This keeps the persistence boundary inside the store instead of scattering sqlite writes across manager and graph code.

### Frontend historical rendering model

The thread renderer should treat progress cards as run-scoped artifacts, not only active-stream artifacts.

Recommended rendering rule:

* For each assistant message with a non-null `run_id`:
  * if that `run_id` matches the currently streaming run and in-memory live progress exists, render the live `ResearchProgressCard`
  * otherwise, render a historical `ResearchProgressCard` derived from `run.progress_events`
* Then render the assistant markdown message below the card when message content exists

This gives a stable thread shape:

* user question
* assistant process card
* assistant final answer

for both live and historical runs.

### Frontend state changes

`useChatStore` should maintain only **live** research stream state in memory. Historical replay should come from loaded conversation detail data.

Suggested split:

* `activeConversation.runs[*].progress_events` -> source of truth for historical replay
* `streamingProgress` / `streamingRunEvents` -> source of truth only for the current active run before reload

After terminal reload:

* the store should drop ephemeral live events
* the reloaded conversation detail should provide the persisted replayable history

### Frontend state changes

`useChatStore` should stop treating research progress as only `streamingAssistantPreview`.

Add dedicated research-stream state such as:

* `streamingRunEvents: ResearchStreamEvent[]`
* `streamingProgress: ResearchProgressState | null`

Suggested behavior:

* On each research SSE event:
  * append a normalized event item for the expandable log
  * update `streamingProgress` from `data.progress` when present
  * still update `streamingAssistantPreview` if `assistant_message.content` exists, to preserve interrupted/completed draft preview compatibility
* On terminal:
  * freeze the final progress state briefly in memory
  * reload the conversation detail as today

### Frontend rendering changes

In `ChatArea`:

* keep existing user / assistant message rendering
* replace the generic `isGenerating` spinner block with `ResearchProgressCard` when the active conversation mode is `research`
* keep the existing chat-mode typing indicator for normal chat turns
* only render markdown preview while there is actual assistant content; do not use empty preview as a loading UI

Potential component split:

* `web/src/components/ResearchProgressCard.tsx`
* `web/src/components/ResearchEventLog.tsx`
* `web/src/lib/research-progress.ts`

`research-progress.ts` should own:

* normalization from raw SSE payload to view model
* phase ordering
* fallback label mapping
* summary metric derivation

This keeps conditional logic out of `ChatArea`.

### Type updates

Add explicit types under `web/src/types/research.ts` for:

* `ResearchProgressPhase`
* `ResearchWorkerStep`
* `ResearchProgressCounts`
* `ResearchTaskProgress`
* `ResearchReviewProgress`
* `ResearchProgressPayload`
* `ResearchRunHistoryEvent`
* narrowed research SSE event payload shape

Avoid leaving `SSEEvent.type` and `data.progress` as loose `string | unknown`.

### Scope boundary

Included in this task:

* thread-native progress card
* structured research SSE progress payload
* low-level expandable event log
* interrupted / failed / completed progress states
* static replay of historical progress cards after reopening a conversation
* persisted research event history storage and hydration

Explicitly out of scope for this task:

* full frontend human-review editing and resume controls
* changing chat-mode streaming behavior
* redesigning the final report renderer itself

## Acceptance Criteria (refined)

* [ ] Active research runs render a dedicated in-thread progress card instead of only a generic spinner.
* [ ] The progress card distinguishes at least the chosen top-level research phases.
* [ ] Research SSE payloads carry structured `progress` metadata consumable by the frontend.
* [ ] Task execution can surface task title, task index, and worker sub-step when available.
* [ ] `run.interrupted` renders an awaiting-review state without pretending the run completed.
* [ ] Reopening a completed research conversation statically re-renders each run's process card from persisted history.
* [ ] Historical replay does not require reopening SSE streams for old runs.
* [ ] Existing chat-mode event streaming remains behaviorally unchanged.
