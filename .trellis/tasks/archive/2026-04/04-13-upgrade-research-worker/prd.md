# Upgrade research_worker

## Goal

Upgrade the current `research_worker` from a single-pass scaffold into a more capable research execution unit that can improve query quality, filter weak web results, and emit higher-confidence evidence for the downstream merge / gap-check / synthesis stages.

## What I already know

* User wants to open a new task and evaluate upgrade approaches for `research_worker`.
* The current worker is a single node at `app/graph/subgraphs/research_worker.py`.
* README already marks `research_worker` as a scaffold and explicitly suggests upgrading it with query rewriting, page filtering, and evidence scoring.
* `dispatch_tasks` fans out one worker call per task and only passes `request` plus a single `task`.
* The worker currently performs `search_web()` -> `fetch_pages()` -> `extract_evidence()` and returns reducer-friendly `raw_findings` plus `raw_source_batches`.
* `merge_evidence` merges sources and deduplicates findings by `task_id + source_id + normalized claim`.
* `gap_check` only reasons on the count of findings per task and on source diversity; it does not know why a task failed.
* The runtime contract allows deterministic fallback when LLM credentials are absent, so any upgrade must preserve a no-LLM path.

## Assumptions (temporary)

* The first phase should prioritize research quality and observability over adding a full autonomous multi-agent runtime.
* Backward compatibility with current graph contracts is preferred unless a stronger worker subgraph clearly justifies schema changes.
* The worker should stay the only place that performs task-level external I/O.

## Open Questions

* In the first implementation phase, should the worker subgraph only preserve the current output contract, or should it also emit structured per-task diagnostics for downstream gap handling and observability?

## Requirements (evolving)

* Preserve current graph-level fan-out model: one logical worker execution per planned task.
* Improve search recall and precision beyond the current two-query scaffold.
* Filter or rank fetched pages before evidence extraction.
* Produce more meaningful evidence claims and more defensible `relevance_score` / `confidence`.
* Keep deterministic fallback behavior when LLM credentials are absent.
* Keep outputs compatible with downstream merge / synthesis unless contract changes are explicitly approved.
* Implement the upgrade as a dedicated worker subgraph rather than a single monolithic worker function.

## Acceptance Criteria (evolving)

* [ ] Approach B is implemented as the approved direction.
* [ ] The chosen direction defines how query generation, page selection, and evidence scoring will work.
* [ ] The chosen direction defines whether graph state / task / evidence contracts must change.
* [ ] The chosen direction preserves or intentionally revises deterministic fallback behavior.

## Definition of Done (team quality bar)

* Tests added or updated where behavior changes.
* Lint and typecheck pass.
* Docs or spec notes updated if contracts change.
* Failure paths and fallback behavior are explicit.

## Out of Scope (explicit)

* Replacing the entire LangGraph runtime.
* Frontend UX redesign for run visualization.
* Broad API redesign unless required by the chosen worker contract.

## Technical Notes

* Relevant files inspected:
  * `README.md`
  * `app/graph/subgraphs/research_worker.py`
  * `app/graph/nodes/dispatcher.py`
  * `app/graph/nodes/merge.py`
  * `app/graph/nodes/gap_check.py`
  * `app/graph/state.py`
  * `app/tools/search.py`
  * `app/tools/fetch.py`
  * `app/tools/extract.py`
  * `app/domain/models.py`
  * `.trellis/spec/backend/research-agent-runtime.md`
  * `docs/current-langgraph-graph.md`
* Current hard constraints:
  * `research_worker` only receives `request` and `task`.
  * Graph reducer fields are `raw_findings` and `raw_source_batches`.
  * No current structured worker-level error channel exists in graph state.
  * Search depends on Tavily when available; fetch and extract degrade gracefully on missing dependencies.

## Research Notes

### Current architecture reading

* The graph treats `research_worker` as the task-level external I/O boundary.
* Downstream nodes assume worker output is append-only and reducer-friendly.
* Current gaps are quality gaps, not orchestration gaps: there is no query rewrite, source qualification, extraction rubric, or structured failure output.
* README hints at a future deepagents-style execution layer, but current graph wiring still assumes a single worker node.

### Feasible approaches here

**Approach A: In-place smart worker** (lowest risk)

* How it works:
  * Keep one `research_worker` node.
  * Add internal stages inside the worker: query rewrite, hit scoring/filtering, page selection, evidence scoring.
  * Preserve current graph contracts.
* Pros:
  * Minimal graph churn.
  * Fastest path to better result quality.
  * Lowest API / state migration cost.
* Cons:
  * Worker file may become large unless split behind services.
  * Failure semantics stay partially implicit unless state contracts are expanded.

**Approach B: Worker subgraph inside LangGraph** (selected)

* How it works:
  * Replace the single worker function with a worker subgraph: rewrite_queries -> search_and_rank -> fetch_and_filter -> extract_and_score -> emit_results.
  * Keep outer graph unchanged, but give the worker an internal retry / fallback structure.
  * Add optional structured metadata such as skipped URLs, failed reasons, or per-task diagnostics.
* Pros:
  * Clear internal responsibilities and easier testing.
  * Stronger foundation for later human review or targeted retries.
  * Preserves current top-level task fan-out.
* Cons:
  * Requires modest state-contract work.
  * More moving parts than Approach A.

### Selected direction details

* Keep the outer graph contract centered on task-level fan-out from `dispatch_tasks`.
* Refactor the current worker into an internal staged flow, likely with these responsibilities:
  * `rewrite_queries`
  * `search_and_rank`
  * `fetch_and_filter`
  * `extract_and_score`
  * `emit_results`
* Keep deterministic fallback behavior at each stage where LLM-dependent logic may be absent.
* Prefer service extraction for pure ranking / scoring logic so the subgraph nodes stay thin.

**Approach C: Deepagents-style autonomous worker runtime** (highest ambition)

* How it works:
  * Treat each planned task as a mini agent loop with tool choice, iterative search, and self-reflection.
  * Worker decides when to rewrite, fetch more, or stop based on evidence quality.
* Pros:
  * Highest ceiling for research depth.
  * Best alignment with README's long-term direction.
* Cons:
  * Biggest implementation and validation cost.
  * Harder deterministic fallback story.
  * Highest risk of state drift, latency growth, and noisy evidence.
