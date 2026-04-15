from __future__ import annotations

from typing import Any

from app.domain.models import AcquiredContent


MIN_PAGE_CHARS = 200
MIN_SNIPPET_CHARS = 80
REMOTE_FALLBACK_REASONS = frozenset({"empty_content", "short_content", "blocked_page"})


def normalize_content_text(value: str) -> str:
    return " ".join(value.split())


def extraction_text_from_metadata(metadata: dict[str, Any]) -> str | None:
    value = metadata.get("extracted_text")
    if not isinstance(value, str):
        return None
    normalized = normalize_content_text(value)
    return normalized or None


def preferred_content_text(item: AcquiredContent) -> str:
    extracted_text = extraction_text_from_metadata(item.metadata)
    if extracted_text is not None:
        return extracted_text
    return normalize_content_text(item.content)


def quality_failure_reason(metadata: dict[str, Any]) -> str | None:
    value = metadata.get("quality_failure_reason")
    if not isinstance(value, str):
        return None
    normalized = normalize_content_text(value)
    return normalized or None


def should_escalate_to_jina_reader(item: AcquiredContent) -> bool:
    if item.acquisition_method not in {"provider_raw_content", "http_fetch"}:
        return False
    return quality_failure_reason(item.metadata) in REMOTE_FALLBACK_REASONS


def should_escalate_to_firecrawl(item: AcquiredContent) -> bool:
    if item.acquisition_method not in {"provider_raw_content", "http_fetch", "jina_reader"}:
        return False
    return quality_failure_reason(item.metadata) in REMOTE_FALLBACK_REASONS


def replace_contents(contents: list[AcquiredContent], replacements: dict[str, AcquiredContent]) -> list[AcquiredContent]:
    if not replacements:
        return contents
    return [replacements.get(item.url, item) for item in contents]
