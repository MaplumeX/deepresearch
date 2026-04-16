# Error Handling

> How errors are handled in this project.

---

## Scenario: LLM Readiness And Fail-Fast Research Generation

### 1. Scope / Trigger
- Trigger: changes to research/chat request validation, LLM capability checks, or service-level model invocation behavior.
- Scope: `app/api/routes.py`, `app/run_manager.py`, `app/chat_manager.py`, `app/services/llm.py`, and LLM-backed services under `app/services/`.

### 2. Signatures

```python
class LLMServiceError(RuntimeError): ...
class LLMNotReadyError(LLMServiceError): ...
class LLMInvocationError(LLMServiceError): ...
class LLMOutputInvalidError(LLMServiceError): ...
class InsufficientEvidenceError(LLMServiceError): ...

def ensure_chat_llm_ready(settings: Settings) -> None
def ensure_planning_llm_ready(settings: Settings) -> None
def ensure_synthesis_llm_ready(settings: Settings) -> None
def ensure_research_llm_ready(settings: Settings) -> None
```

### 3. Contracts

- `ChatConversationManager._create_turn()` must call `ensure_chat_llm_ready()` before any turn is persisted.
- `ResearchRunManager._create_turn()` must call `ensure_research_llm_ready()` before any run is persisted.
- `routes.py` must map `LLMNotReadyError` raised by create endpoints to `HTTP 503`.
- LLM-backed service functions must raise:
  - `LLMInvocationError` for dependency / model / network / provider failures
  - `LLMOutputInvalidError` for structurally invalid or unusable model output
  - `InsufficientEvidenceError` when synthesis cannot proceed because the evidence set is empty

### 4. Validation & Error Matrix

| Condition | Validation point | Behavior |
|-----------|------------------|----------|
| research create request arrives without configured LLM | `ResearchRunManager._create_turn()` | raise `LLMNotReadyError`; route returns `503`; no queued run is created |
| chat create request arrives without configured LLM | `ChatConversationManager._create_turn()` | raise `LLMNotReadyError`; route returns `503`; no chat turn is created |
| service cannot import LangChain prompt helpers | service entrypoint | raise `LLMInvocationError` |
| service cannot build a structured chat model | service entrypoint | raise `LLMInvocationError` |
| model returns syntactically valid but contract-invalid payload | service post-validation | raise `LLMOutputInvalidError` |
| synthesis is called with zero findings | `synthesize_report()` | raise `InsufficientEvidenceError` |

### 5. Good/Base/Bad Cases

- Good:
  research request with valid LLM settings creates a queued run and starts background execution.
- Base:
  research request without LLM settings returns `503` immediately and leaves persistence unchanged.
- Bad:
  service swallows `LLMInvocationError` and fabricates deterministic content to keep the run green.

### 6. Tests Required

- Unit test research create paths reject missing LLM readiness before queueing work.
- Unit test chat create paths reject missing LLM readiness before queueing work.
- Unit test planning/query rewrite/synthesis/chat/evidence extraction raise explicit LLM errors instead of returning fallback content.

### 7. Wrong vs Correct

#### Wrong

```python
def plan_research_tasks(...):
    planned = maybe_plan_with_llm(...)
    if planned is None:
        return build_default_plan()
```

#### Correct

```python
def plan_research_tasks(...):
    ensure_planning_llm_ready(settings)
    planned = plan_with_llm(...)
    if not planned.tasks:
        raise LLMOutputInvalidError("Research planning returned no tasks.")
    return planned
```
