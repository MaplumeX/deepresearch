# Analyze Current LangGraph Graph

## Goal
Analyze the current LangGraph-based deep research workflow in the backend and document the graph structure, state contract, node responsibilities, routing rules, and runtime interaction in a Markdown document.

## Requirements
- Inspect the current LangGraph implementation from graph builder to runtime entry points.
- Identify graph nodes, edges, conditional routing, interrupt/resume behavior, and key state fields.
- Document how the graph is invoked from the runtime and run manager layers.
- Write the analysis into a Markdown file under the task directory.

## Acceptance Criteria
- [ ] The document lists the current graph nodes and the main execution flow in order.
- [ ] The document explains conditional branches and interrupt/resume behavior.
- [ ] The document summarizes the graph state structure and major state transitions.
- [ ] The document references the main source files that define the current behavior.

## Technical Notes
- Scope is limited to the current backend implementation in `app/graph/`, `app/runtime.py`, and related run orchestration files.
- The document should describe the code as it exists now rather than proposing a redesign.
