# Analyze Deep Research Flow

## Goal
Document how the deep research flow works across the backend runtime, graph orchestration, persistence layer, API surface, and frontend consumption.

## Requirements
- Trace the main execution path for creating and resuming a research run.
- Identify the major modules, responsibilities, and dependency direction.
- Describe how frontend pages and hooks interact with backend APIs and SSE events.
- Produce the analysis in a repository Markdown document with concrete file references.

## Acceptance Criteria
- [ ] The document explains the end-to-end flow from user input to final report.
- [ ] The document distinguishes explicit facts from reasonable inferences where needed.
- [ ] The document references the main files that implement the flow.
- [ ] The document is saved as a Markdown file in the repository.

## Technical Notes
- Scope is analysis and documentation only; no behavioral change is required.
- The flow spans frontend and backend, so cross-layer tracing is required.
