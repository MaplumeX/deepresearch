from __future__ import annotations

from typing import Any

from app.config import Settings


class LLMServiceError(RuntimeError):
    """Base class for LLM-related service failures."""


class LLMNotReadyError(LLMServiceError):
    """Raised when a workflow requires an LLM but the runtime is not ready."""


class LLMInvocationError(LLMServiceError):
    """Raised when an LLM call fails and the workflow should stop."""


class LLMOutputInvalidError(LLMServiceError):
    """Raised when an LLM response does not satisfy the expected contract."""


class InsufficientEvidenceError(LLMServiceError):
    """Raised when synthesis cannot continue with the available evidence."""


def can_use_llm(settings: Settings) -> bool:
    return bool(settings.llm_api_key or settings.llm_base_url)


def ensure_chat_llm_ready(settings: Settings) -> None:
    if can_use_llm(settings):
        return
    raise LLMNotReadyError(
        "Chat mode requires a configured LLM. Set `LLM_API_KEY` or `OPENAI_API_KEY`, "
        "or provide a compatible `LLM_BASE_URL`.",
    )


def ensure_planning_llm_ready(settings: Settings) -> None:
    if not can_use_llm(settings):
        raise LLMNotReadyError(
            "Research mode requires a configured LLM. Set `LLM_API_KEY` or `OPENAI_API_KEY`, "
            "or provide a compatible `LLM_BASE_URL`.",
        )
    if not settings.enable_llm_planning:
        raise LLMNotReadyError("Research mode requires `ENABLE_LLM_PLANNING=true`.")


def ensure_synthesis_llm_ready(settings: Settings) -> None:
    if not can_use_llm(settings):
        raise LLMNotReadyError(
            "Research mode requires a configured LLM. Set `LLM_API_KEY` or `OPENAI_API_KEY`, "
            "or provide a compatible `LLM_BASE_URL`.",
        )
    if not settings.enable_llm_synthesis:
        raise LLMNotReadyError("Research mode requires `ENABLE_LLM_SYNTHESIS=true`.")


def ensure_research_llm_ready(settings: Settings) -> None:
    ensure_planning_llm_ready(settings)
    ensure_synthesis_llm_ready(settings)


def build_chat_model(
    model_name: str,
    settings: Settings,
    temperature: float = 0,
    *,
    use_responses_api: bool | None = None,
    use_previous_response_id: bool = False,
):
    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        return None

    kwargs = {
        "model": model_name,
        "temperature": temperature,
    }

    if use_responses_api is not None:
        kwargs["use_responses_api"] = use_responses_api
    if use_previous_response_id:
        kwargs["use_previous_response_id"] = True

    if settings.llm_base_url:
        kwargs["base_url"] = settings.llm_base_url

    if settings.llm_api_key:
        kwargs["api_key"] = settings.llm_api_key
    elif settings.llm_base_url:
        # Many OpenAI-compatible gateways accept a dummy key or no auth.
        # Passing a placeholder keeps the client usable for those endpoints.
        kwargs["api_key"] = "openai-compatible-placeholder"

    return ChatOpenAI(**kwargs)


def build_structured_chat_model(
    model_name: str,
    settings: Settings,
    schema: Any,
    temperature: float = 0,
):
    model = build_chat_model(model_name, settings, temperature=temperature)
    if model is None or not hasattr(model, "with_structured_output"):
        return None

    try:
        return model.with_structured_output(schema)
    except Exception:
        return None
