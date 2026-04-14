from __future__ import annotations

from collections.abc import Callable, Iterable

from app.config import Settings
from app.domain.models import ResearchConversationDetail
from app.services.llm import build_chat_model, can_use_llm


SYSTEM_PROMPT = (
    "You are a helpful general assistant. "
    "Answer directly, stay grounded in the conversation history, and keep the response concise when the user asks a direct question."
)


async def generate_chat_reply(
    settings: Settings,
    conversation: ResearchConversationDetail,
    on_chunk: Callable[[str], None] | None = None,
) -> str:
    latest_question = _latest_user_question(conversation)
    if not latest_question:
        return "请提供一个具体问题。"

    model = build_chat_model(settings.synthesis_model, settings, temperature=0.3)
    if not can_use_llm(settings) or model is None:
        return _deterministic_fallback(latest_question)

    try:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    except ImportError:
        return _deterministic_fallback(latest_question)

    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for message in conversation.messages:
        content = message.content.strip()
        if not content:
            continue
        if message.role == "user":
            messages.append(HumanMessage(content=content))
        else:
            messages.append(AIMessage(content=content))

    content_parts: list[str] = []
    async for chunk in model.astream(messages):
        text = _coerce_text(chunk.content)
        if not text:
            continue
        content_parts.append(text)
        if on_chunk is not None:
            on_chunk("".join(content_parts))

    full_content = "".join(content_parts)
    return full_content.strip() or "我暂时没有生成有效回复，请换个表述再试一次。"


def _latest_user_question(conversation: ResearchConversationDetail) -> str:
    for message in reversed(conversation.messages):
        if message.role == "user" and message.content.strip():
            return message.content.strip()
    return ""


def _deterministic_fallback(question: str) -> str:
    return (
        "当前已进入普通对话模式，但服务端尚未配置可用的大模型。\n\n"
        f"你的问题是：{question}\n\n"
        "如需获得真实回答，请配置 `LLM_API_KEY` 或 `OPENAI_API_KEY`，"
        "也可以通过 `LLM_BASE_URL` 接入兼容网关。"
    )


def _coerce_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(_coerce_text(item) for item in content)
    if isinstance(content, dict):
        text = content.get("text")
        return text if isinstance(text, str) else ""
    if isinstance(content, Iterable):
        return "".join(_coerce_text(item) for item in content)
    return ""
