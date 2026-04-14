# Structured Report Contract For Deep Research

## Goal
Replace the current markdown-only report flow with a structured report contract that keeps markdown for compatibility while exposing first-class section, citation, and source metadata for higher-quality rendering and auditing.

## Requirements
- Add a structured report payload to synthesis output without breaking existing `draft_report` and `final_report` fields.
- Preserve deterministic fallback behavior when LLM synthesis is disabled.
- Strengthen report audit checks around citation coverage and report structure.
- Update the run detail UI to render structured sections, clickable citations, and source cards while keeping markdown compatibility.
- Add or update unit tests for synthesis, citations, and UI rendering behavior.

## Acceptance Criteria
- [ ] Run results include structured report data alongside markdown report text.
- [ ] Citation metadata links rendered report citations to known sources.
- [ ] Audit catches missing or inconsistent citation/report structure issues.
- [ ] Run detail page renders structured report sections and source cards when present.
- [ ] Backend and frontend tests cover the new contract.

## Technical Notes
- This change spans backend report synthesis, audit logic, runtime result contract, frontend types, and report rendering.
- Keep logic isolated in services and avoid pushing orchestration into tools or view components.
- Maintain backward compatibility for existing stored runs that only contain markdown fields.
