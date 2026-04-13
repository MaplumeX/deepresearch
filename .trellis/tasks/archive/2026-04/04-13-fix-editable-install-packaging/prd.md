# Fix editable install packaging

## Goal
Allow `pip install -e ".[dev]"` to succeed in a fresh virtual environment.

## Requirements
- Configure Hatch wheel packaging explicitly for the repository's actual package root.
- Keep the package layout unchanged and avoid introducing unnecessary build complexity.
- Preserve the existing dependency declarations and development extras.

## Acceptance Criteria
- [ ] Editable metadata generation succeeds for the project.
- [ ] `pip install -e ".[dev]"` can resolve the package without wheel file selection errors.
- [ ] The fix is limited to packaging configuration unless verification reveals another blocker.

## Technical Notes
- The project package root is `app/`, while the project name is `deepresearch`.
- Hatchling needs explicit file selection when the shipped package directory does not match the project name.
