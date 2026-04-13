# Fix planning tests for settings rename

## Goal
Restore the planning unit tests after the settings field rename from OpenAI-specific names to generic LLM names.

## Requirements
- Update the planning unit test to construct `Settings` with the current dataclass signature.
- Keep the runtime code and environment contract unchanged.
- Limit the fix to the stale test unless verification reveals another related test issue.

## Acceptance Criteria
- [ ] `tests/unit/test_planning.py` uses the current `Settings` fields.
- [ ] Unit tests pass for the planning and config test modules.
- [ ] The fix does not change backend runtime behavior.

## Technical Notes
- `Settings` now uses `llm_api_key` and `llm_base_url`.
- The runtime still accepts `OPENAI_*` environment variables as fallback aliases inside `get_settings()`.
