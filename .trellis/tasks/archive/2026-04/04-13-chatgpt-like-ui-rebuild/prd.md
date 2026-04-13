# brainstorm: redesign web ui like chatgpt

## Goal

Redesign the current web application into a ChatGPT-like research workspace so the product feels conversational, focused, and continuous instead of looking like a traditional operations console. The redesign should make starting a run, switching history, reading streaming progress, and reviewing the final report feel like one coherent workflow.

## What I already know

* The user wants a broad UI refactor and explicitly allows large-scope changes.
* The current frontend lives in `web/` and uses React + Vite + React Router + React Query.
* The current app is split into separate pages for home, run history, and run detail.
* `AppLayout` already provides a left sidebar, but the interaction model still feels like a dashboard with separate screens.
* `HomePage` is currently form-first and field-heavy, closer to an admin console than a conversational composer.
* `RunDetailPage` already contains the right core data for a ChatGPT-like workspace: prompt, report, warnings, live events, and human review.
* Styling is centralized in `web/src/styles.css`, so a large visual refactor is feasible without introducing a new styling stack.
* There is an archived brainstorm task with similar direction, which confirms the repo has already explored a ChatGPT-like workspace shell.

## Assumptions (temporary)

* This task is primarily a frontend redesign, not a backend contract rewrite.
* Existing run creation, detail loading, SSE event streaming, and resume-review flows should be preserved.
* "More like ChatGPT" means conversation-first layout, lighter chrome, tighter visual hierarchy, and a stronger composer/history workflow.
* It is acceptable to keep current routes if the shell and page composition become cohesive enough.

## Open Questions

* None currently blocking.

## Requirements (evolving)

* Replace the current console-like shell with a ChatGPT-inspired workspace.
* Make recent runs/history the primary navigation surface.
* Reframe run creation as a prompt composer, not a settings-heavy form block.
* Make the selected run page feel like one research conversation/workbench.
* Remodel the main selected-run experience into a threaded conversation timeline instead of separate dashboard panels.
* Present the original user prompt, run progress, final report, warnings, and review actions as thread-native content blocks where practical.
* Support the product direction where users can continue asking follow-up questions or branch a new research flow from an existing result.
* Preserve current core capabilities: create run, open history, inspect live progress, inspect final report, resume interrupted review.
* Keep desktop and mobile layouts usable.
* Avoid unnecessary backend changes unless the chosen UI direction truly requires them.

## Acceptance Criteria (evolving)

* [x] Existing frontend structure and constraints are documented.
* [x] A ChatGPT-like target interaction model is described in concrete UI terms.
* [x] Feasible implementation approaches are identified.
* [x] The redesign depth is explicitly chosen.
* [x] The MVP scope boundary is explicitly chosen.
* [x] The chosen direction preserves existing core flows.

## Definition of Done (team quality bar)

* The chosen UI direction is implemented without breaking existing run flows.
* Updated behavior has test coverage where rendering or interaction logic changes.
* Frontend typecheck and tests pass.
* Responsive behavior is validated for common desktop and mobile breakpoints.

## Out of Scope (explicit)

* Backend runtime redesign unrelated to the UI goal.
* Authentication, multi-user workspace, or permissions model changes.
* A speculative feature expansion beyond what improves the ChatGPT-like workspace itself.

## Technical Notes

* Relevant files inspected:
  * `web/src/components/AppLayout.tsx`
  * `web/src/components/RunForm.tsx`
  * `web/src/components/RunSummaryTable.tsx`
  * `web/src/components/ReviewPanel.tsx`
  * `web/src/pages/HomePage.tsx`
  * `web/src/pages/RunsPage.tsx`
  * `web/src/pages/RunDetailPage.tsx`
  * `web/src/app/router.tsx`
  * `web/src/styles.css`
  * `web/package.json`
* Current repo constraints:
  * Route structure already exists and can be preserved or repurposed.
  * React Query owns server state and should remain the data-fetching boundary.
  * SSE-driven live activity already exists and is suitable for a streaming workspace.
  * The styling system is a single shared stylesheet, so refactoring can stay simple and centralized.

## Research Notes

### What the current product already has

* A persistent history/sidebar concept already exists.
* The run detail page already contains the ingredients for a conversation-style workspace.
* The biggest gap is interaction framing and information hierarchy, not missing backend data.

### ChatGPT-like conventions that fit this product

* Left sidebar for session switching and "new research".
* A composer-first home state with one dominant action.
* A narrow, readable main content column for prompt/report content.
* Streaming progress presented inline or in a lightweight supporting rail instead of as a heavy admin panel.
* Low-chrome light UI with stronger typography and fewer bordered boxes.

### Design-system guidance gathered

* Recommended style direction: AI-native minimal UI.
* Recommended layout bias: single dominant content column with limited chrome.
* Recommended typography mood: editorial + accessible, suitable for long-form research reading.
* Important UX constraints:
  * avoid content jump during streaming
  * keep text width constrained for readability
  * avoid overlapping fixed elements on mobile
  * announce dynamic content accessibly when activity updates

### Feasible approaches here

**Approach A: Visual reskin only**

* Keep existing routes and page structure.
* Mainly refactor styles, spacing, cards, and typography.
* Lowest risk and fastest.
* Weakest resemblance to ChatGPT at the interaction level.

**Approach B: Unified workspace shell** (Recommended)

* Keep current data hooks and routes, but redesign the shell around sidebar + composer + continuous workspace.
* Convert home into a centered composer landing state.
* Convert detail into a research workbench with a dominant reading column and lighter supporting activity/metadata areas.
* Best balance between fidelity, scope, and implementation safety.

**Approach C: Full chat-thread workbench** (Chosen)

* Go beyond shell changes and remodel the main experience into a threaded conversation timeline:
  * user prompt bubble
  * assistant progress blocks
  * report rendered as an assistant response
  * review actions embedded as in-thread controls
* Highest fidelity to ChatGPT.
* Likely requires broader component reshaping and possibly some frontend state reshaping.

## Decision (ADR-lite)

**Context**: The user wants the product to feel much more like ChatGPT and explicitly allows broad UI changes. A shell-only redesign would improve appearance but would not fundamentally change the interaction model.

**Decision**: Use the full chat-thread workbench approach as the redesign target for this task.

**Consequences**:

* `RunDetailPage` will likely be restructured around a conversation timeline rather than dual dashboard columns.
* `RunForm`, `ReviewPanel`, and live-event presentation will likely need stronger component reshaping than in a shell-only redesign.
* Route compatibility can still be preserved, but page internals will change more aggressively.
* Thread semantics will be introduced as a product-level conversation model rather than remaining a frontend illusion.

## Backend Implication Notes

* The current backend model is run-centric, not conversation-centric.
* `run_id` is currently both:
  * the business run identifier
  * the LangGraph checkpoint `thread_id`
* The persisted store only has `research_runs` with per-run request/result snapshots.
* The current API supports:
  * create run
  * list runs
  * get run
  * stream run events
  * resume interrupted run
* The existing `resume` flow is for human-review continuation inside the same run, not for general follow-up questioning.
* This means a true ChatGPT-like "continue the same conversation" experience is not fully modeled in the backend today.

## Feasible Backend Paths For Option 3

**Path 1: Frontend-stitched pseudo thread**

* Keep backend run-centric.
* Add lightweight linkage like `parent_run_id` / `source_run_id` so a new run can declare what it follows from.
* The frontend renders a sequence of linked runs as one conversation thread.
* Lowest backend cost, but semantics are "thread of runs", not a true single conversation state.

**Path 2: Hybrid conversation model** (Chosen)

* Introduce a first-class `conversation_id` / `thread_id` at the product level.
* A conversation owns many runs/messages.
* Each follow-up question creates a new run within one conversation, while each run can still map to its own LangGraph execution/checkpoint.
* Best balance between ChatGPT-like UX and compatibility with the current execution engine.

**Path 3: Full backend thread unification**

* Redesign the runtime so one backend thread/conversation directly maps to iterative, multi-turn execution state.
* Highest fidelity, but it entangles product conversation semantics with LangGraph execution semantics much more deeply.
* Highest scope and migration risk for this task.

## Technical Approach

* Introduce a product-level conversation model in the backend instead of treating each run as a standalone UI unit.
* Keep the existing execution engine largely run-centric:
  * each user turn that triggers research creates a new run
  * each run keeps its own LangGraph checkpoint lifecycle
* Add linkage between conversations, user turns, assistant outputs, and runs so the frontend can render a true threaded workspace.
* Refactor the web shell into a ChatGPT-like app structure:
  * left conversation history
  * central thread view
  * bottom composer
  * lightweight supporting metadata/activity surfaces
* Make the thread the default product surface, with the old page split dissolved into one continuous conversation workspace.
