# brainstorm: chatgpt-like-ui

## Goal

Redesign the current web UI into a ChatGPT-like research workspace so the product feels conversational and task-oriented instead of dashboard-like. The redesign should improve information hierarchy, reduce visual chrome, and make creating a run, browsing history, and reading live research progress feel like one continuous workflow.

## What I already know

* User wants a new task focused on optimizing the current UI to feel more like ChatGPT.
* The current frontend lives in `web/` and uses React + Vite + React Router + React Query.
* The app currently uses a top navigation with separate routes for home, run history, and run detail.
* `HomePage` is a two-column dashboard with a creation form on the left and recent runs on the right.
* `RunDetailPage` is a report-first detail screen with a right-side realtime activity panel.
* Styling is centralized in `web/src/styles.css`, so a first UI redesign can stay mostly inside route components plus the shared stylesheet.
* Existing frontend structure already separates pages, components, hooks, and typed contracts, which makes a shell/layout refactor feasible without rewriting data flow.

## Assumptions (temporary)

* This task is primarily a frontend redesign, not a backend/API redesign.
* The first version should preserve the current run creation and run detail capabilities.
* A ChatGPT-like experience here means conversation/workspace layout, lighter chrome, strong typography, left-side history, and a focused composer area.
* It is acceptable to keep the existing route model if the UI shell still feels cohesive.

## Open Questions

* None currently blocking. The first implementation will follow the approved workspace-shell direction.

## Requirements (evolving)

* Replace the current dashboard-style shell with a ChatGPT-inspired workspace layout.
* Make history/navigation feel closer to a left sidebar instead of a top navigation bar.
* Make the create-run experience feel like a prompt composer rather than an admin form.
* Preserve current core flows: create run, browse runs, open run detail, inspect report/activity, resume interrupted review.
* Keep the implementation aligned with existing frontend state/data-fetching patterns.
* Keep the design responsive for desktop and mobile.
* Preserve route-level compatibility while making the shell feel like one continuous product surface.
* Reduce visual chrome and avoid dashboard-style metric/panel composition.

## Acceptance Criteria (evolving)

* [x] The approved redesign scope is explicit.
* [x] The target information architecture is explicit.
* [x] The first implementation phase identifies which existing pages/components will be retained, merged, or restyled.
* [ ] The redesign preserves current functional flows.

## Definition of Done (team quality bar)

* UI changes are implemented without breaking existing run flows.
* Tests are updated where behavior changes.
* Typecheck and frontend tests pass.
* Responsive behavior is verified at common breakpoints.

## Out of Scope (explicit)

* Backend research runtime changes.
* Authentication / multi-user product expansion.
* A full product rewrite beyond the existing frontend application.

## Technical Notes

* Relevant files inspected:
  * `web/src/components/AppLayout.tsx`
  * `web/src/components/RunForm.tsx`
  * `web/src/components/ReviewPanel.tsx`
  * `web/src/pages/HomePage.tsx`
  * `web/src/pages/RunsPage.tsx`
  * `web/src/pages/RunDetailPage.tsx`
  * `web/src/app/router.tsx`
  * `web/src/styles.css`
  * `web/package.json`
* Relevant frontend guidance inspected:
  * `.trellis/spec/frontend/directory-structure.md`
  * `.trellis/spec/frontend/state-management.md`
  * `.trellis/spec/frontend/type-safety.md`
  * `.trellis/spec/guides/code-reuse-thinking-guide.md`
* Current frontend constraints:
  * Styling is centralized in one stylesheet.
  * Route-level structure is page-based.
  * Server state is owned by React Query and SSE hooks.
  * Existing run status/report/event contracts should be reused instead of redefined.

## Research Notes

### Current UI structure

* The current product feels like an operations console rather than an AI conversation workspace.
* Most user value is split across three separate screens: create, list, and detail.
* The data flow is already good enough to support a better shell without changing backend contracts.

### Comparable ChatGPT-like conventions

* Left sidebar for history and session switching.
* Centered composer-first landing state.
* Conversation/report thread as the main content column.
* Secondary metadata and activity moved into lighter supporting panels instead of dominant layout regions.
* Low-chrome light UI, high readability, clear focus states, and strong async/loading feedback.

### Feasible approaches here

**Approach A: Visual reskin only**

* Keep existing routes and page structure.
* Replace topbar and dashboard styling with a ChatGPT-like shell, sidebar, and cleaner cards.
* Lowest risk, fastest delivery.
* Limitation: product flow still feels separated across pages.

**Approach B: Workspace shell refactor** (Approved)

* Keep current backend/data hooks but reorganize the frontend into a unified workspace shell.
* Add a persistent left history sidebar and make home/detail feel like one continuous research workspace.
* Better match for the requested ChatGPT-like experience.
* Moderate scope, but still feasible inside the current architecture.

### Approved first-phase information architecture

* Keep routing compatible:
  * `/` remains the entry for starting a new research run.
  * `/runs/:runId` remains the focused workspace for a selected run.
  * `/runs` can remain as a full history view, but sidebar history becomes the primary navigation path.
* Replace the top navigation bar with a persistent app shell:
  * Left sidebar: app identity, new research entry point, recent runs/history navigation.
  * Main workspace: prompt composer on home, report/activity workspace on detail.
* Reframe the home page as a centered composer-first landing state.
* Reframe the detail page as a research conversation/workbench:
  * main column for report and review actions
  * secondary column for metadata and live activity
* Retain current core components where possible, but restyle and reposition them:
  * `AppLayout`: replace with workspace shell
  * `RunForm`: transform from admin form to composer layout
  * `RunSummaryTable`: split or restyle toward sidebar/history usage
  * `RunDetailPage`: adopt workspace composition
  * `ReviewPanel`: visually integrate into the report thread/workbench

**Approach C: Interaction model redesign**

* Go beyond layout and turn the report page into a true chat-style threaded interaction model.
* Highest fidelity to ChatGPT, but it implies larger content-model and interaction changes.
* Highest risk for first iteration.
