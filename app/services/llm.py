from __future__ import annotations

from typing import Any

from app.config import Settings


def can_use_llm(settings: Settings) -> bool:
    return bool(settings.llm_api_key or settings.llm_base_url)


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
