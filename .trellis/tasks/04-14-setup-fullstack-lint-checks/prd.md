# Setup Frontend and Backend Lint Checks

## Goal
Build repeatable lint checks for both frontend and backend so contributors can run and validate code quality consistently from the repository.

## Requirements
- Add or fix backend lint configuration and runnable commands.
- Add or fix frontend lint configuration and runnable commands.
- Keep the setup aligned with existing project structure and dependencies.
- Avoid changing unrelated runtime behavior while introducing lint checks.

## Acceptance Criteria
- [x] Backend lint can be executed with a documented repository command.
- [x] Frontend lint can be executed with a documented repository command.
- [x] Required config files and scripts are checked into the repository.
- [x] Lint commands run successfully in the local workspace, or remaining blockers are documented clearly.

## Technical Notes
- This task is fullstack because it touches backend and frontend tooling.
- Prefer existing linters or conventions already present in the repository before introducing new tools.
