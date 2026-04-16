from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from app.config import Settings
from app.domain.models import ConversationMessage
from app.domain.models import ResearchConversationDetail
from app.services.llm import (
    LLMInvocationError,
    LLMOutputInvalidError,
    build_chat_model,
    ensure_chat_llm_ready,
)


SYSTEM_PROMPT = (
    "You are a helpful general assistant. "
    "Answer directly, stay grounded in the conversation history, and keep the response concise when the user asks a direct question."
)


@dataclass(frozen=True, slots=True)
class ChatReplyResult:
    text: str
    provider_message_id: str | None = None


async def generate_chat_reply(
    settings: Settings,
    conversation: ResearchConversationDetail,
    on_chunk: Callable[[str, str | None], None] | None = None,
) -> ChatReplyResult:
    latest_question = _latest_user_question(conversation)
    if not latest_question:
        return ChatReplyResult(text="请提供一个具体问题。")

    ensure_chat_llm_ready(settings)
    model = build_chat_model(
        settings.synthesis_model,
        settings,
        temperature=0.3,
        use_responses_api=True,
        use_previous_response_id=True,
    )
    if model is None:
        raise LLMInvocationError("Chat model could not be initialized.")

    try:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    except ImportError as exc:
        raise LLMInvocationError("Chat dependencies are not installed.") from exc

    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for message in conversation.messages:
        if message.role == "user":
            content = message.content.strip()
            if not content:
                continue
            messages.append(HumanMessage(content=content))
        else:
            ai_message = _assistant_message_for_model(message, AIMessage)
            if ai_message is not None:
                messages.append(ai_message)

    content_parts: list[str] = []
    provider_message_id: str | None = None
    try:
        async for chunk in model.astream(messages):
            provider_message_id = provider_message_id or _extract_provider_message_id(chunk)
            text = _message_text(chunk)
            if not text:
                continue
            content_parts.append(text)
            if on_chunk is not None:
                on_chunk("".join(content_parts), provider_message_id)
    except Exception as exc:
        raise LLMInvocationError("Chat reply generation failed.") from exc

    full_content = "".join(content_parts)
    text = full_content.strip()
    if not text:
        raise LLMOutputInvalidError("Chat reply returned no content.")
    return ChatReplyResult(text=text, provider_message_id=provider_message_id)


def _latest_user_question(conversation: ResearchConversationDetail) -> str:
    for message in reversed(conversation.messages):
        if message.role == "user" and message.content.strip():
            return message.content.strip()
    return ""

def _assistant_message_for_model(message: ConversationMessage, ai_message_cls):
    content = message.content.strip()
    provider_message_id = _normalize_provider_message_id(message.provider_message_id)
    if not content and provider_message_id is None:
        return None

    response_metadata = {"id": provider_message_id} if provider_message_id is not None else {}
    return ai_message_cls(
        content=content,
        response_metadata=response_metadata,
        id=provider_message_id,
    )


def _message_text(message: object) -> str:
    text = getattr(message, "text", None)
    if isinstance(text, str):
        return text

    content = getattr(message, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(_block_text(item) for item in content)
    return ""


def _block_text(item: object) -> str:
    if not isinstance(item, dict):
        return ""
    text = item.get("text")
    return text if isinstance(text, str) else ""


def _extract_provider_message_id(message: object) -> str | None:
    response_metadata = getattr(message, "response_metadata", None)
    if isinstance(response_metadata, dict):
        response_id = _normalize_provider_message_id(response_metadata.get("id"))
        if response_id is not None:
            return response_id

    return _normalize_provider_message_id(getattr(message, "id", None))


def _normalize_provider_message_id(value: object) -> str | None:
    if isinstance(value, str) and value.startswith("resp_"):
        return value
    return None
