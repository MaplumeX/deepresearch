from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re
from typing import Any

from app.domain.models import AcquiredContent, SourceDocument
from app.services.source_content import MIN_PAGE_CHARS, extraction_text_from_metadata, normalize_content_text, quality_failure_reason


_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_INTERSTITIAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("captcha", re.compile(r"captcha|验证码|人机验证", re.IGNORECASE)),
    ("access_denied", re.compile(r"access denied|访问受限|无权访问|拒绝访问", re.IGNORECASE)),
    ("verify_human", re.compile(r"verify you are human|安全验证|请先验证|完成验证", re.IGNORECASE)),
    ("enable_javascript", re.compile(r"enable javascript|启用javascript|开启javascript|enable cookies", re.IGNORECASE)),
    ("wechat_client_required", re.compile(r"微信客户端打开|微信内打开|请在微信中打开", re.IGNORECASE)),
    ("content_unavailable", re.compile(r"内容已删除|文章已被删除|页面不存在|内容不存在", re.IGNORECASE)),
)
_INTERSTITIAL_TEXT_LIMIT = 600
_DROP_SELECTORS = ("script", "style", "noscript", "nav", "footer", "header", "aside", "form", "iframe", "svg", "canvas")
_ARTICLE_SELECTORS = (
    "article",
    "main",
    "[role=main]",
    ".rich_media_content",
    "#img-content",
    ".RichContent-inner",
    ".Article-content",
    ".article-content",
    ".post-content",
)


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    text: str
    extractor: str
    interstitial_markers: list[str] = field(default_factory=list)
    quality_failure_reason: str | None = None


def build_extraction_metadata(raw_content: str, content_format: str) -> dict[str, Any]:
    result = extract_main_text(raw_content, content_format)
    metadata: dict[str, Any] = {
        "extracted_text": result.text,
        "extractor": result.extractor,
    }
    if result.interstitial_markers:
        metadata["interstitial_markers"] = list(result.interstitial_markers)
    if result.quality_failure_reason is not None:
        metadata["quality_failure_reason"] = result.quality_failure_reason
    return metadata


def extract_main_text(raw_content: str, content_format: str) -> ExtractionResult:
    if content_format in {"text", "markdown"}:
        text = normalize_content_text(raw_content)
        markers = _detect_interstitial_markers(text)
        return ExtractionResult(
            text=text,
            extractor="passthrough",
            interstitial_markers=markers,
            quality_failure_reason=_classify_quality_failure(text, markers),
        )

    cleaned_html, selectolax_text = _extract_with_selectolax(raw_content)
    best_text = selectolax_text
    extractor = "selectolax"
    markers = _detect_interstitial_markers(selectolax_text)

    if _classify_quality_failure(selectolax_text, markers) != "blocked_page":
        trafilatura_text = _extract_with_trafilatura(cleaned_html)
        if _prefer_candidate(trafilatura_text, best_text):
            best_text = trafilatura_text
            extractor = "trafilatura"

        readability_text = _extract_with_readability(cleaned_html)
        if _prefer_candidate(readability_text, best_text):
            best_text = readability_text
            extractor = "readability-lxml"

    if not best_text:
        best_text = _fallback_strip_tags(cleaned_html or raw_content)
        extractor = "regex"

    markers = _detect_interstitial_markers(best_text or selectolax_text)
    return ExtractionResult(
        text=best_text,
        extractor=extractor,
        interstitial_markers=markers,
        quality_failure_reason=_classify_quality_failure(best_text, markers),
    )


def _make_source_id(url: str) -> str:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return f"S{digest}"


def extract_sources(contents: list[AcquiredContent]) -> list[SourceDocument]:
    sources: list[SourceDocument] = []

    for item in contents:
        result = _extraction_result_for_item(item)
        if result.quality_failure_reason == "blocked_page":
            continue

        content = result.text
        if not content:
            continue

        source_id = _make_source_id(item.url)
        sources.append(
            SourceDocument(
                source_id=source_id,
                url=item.url,
                title=item.title or item.url,
                content=content,
                fetched_at=item.acquired_at,
                providers=list(item.providers),
                acquisition_method=item.acquisition_method,
                metadata={
                    **item.metadata,
                    "extractor": result.extractor,
                    "interstitial_markers": list(result.interstitial_markers),
                    "quality_failure_reason": result.quality_failure_reason,
                    "content_format": item.content_format,
                },
            )
        )

    return sources


def _extraction_result_for_item(item: AcquiredContent) -> ExtractionResult:
    extracted_text = extraction_text_from_metadata(item.metadata)
    if extracted_text is not None:
        markers = _metadata_markers(item.metadata)
        return ExtractionResult(
            text=extracted_text,
            extractor=_metadata_extractor(item.metadata),
            interstitial_markers=markers,
            quality_failure_reason=quality_failure_reason(item.metadata) or _classify_quality_failure(extracted_text, markers),
        )
    return extract_main_text(item.content, item.content_format)


def _metadata_extractor(metadata: dict[str, Any]) -> str:
    value = metadata.get("extractor")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "passthrough"


def _metadata_markers(metadata: dict[str, Any]) -> list[str]:
    value = metadata.get("interstitial_markers")
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


def _detect_interstitial_markers(text: str) -> list[str]:
    normalized = normalize_content_text(text).casefold()
    if not normalized:
        return []

    matches: list[str] = []
    for marker, pattern in _INTERSTITIAL_PATTERNS:
        if pattern.search(normalized):
            matches.append(marker)
    return matches


def _classify_quality_failure(text: str, interstitial_markers: list[str]) -> str | None:
    normalized = normalize_content_text(text)
    if not normalized:
        return "empty_content"
    if interstitial_markers and len(normalized) <= _INTERSTITIAL_TEXT_LIMIT:
        return "blocked_page"
    if len(normalized) < MIN_PAGE_CHARS:
        return "short_content"
    return None


def _prefer_candidate(candidate: str, current: str) -> bool:
    if not candidate:
        return False
    if not current:
        return True
    return len(candidate) >= max(len(current) + 80, MIN_PAGE_CHARS)


def _extract_with_trafilatura(raw_content: str) -> str:
    try:
        import trafilatura
    except ImportError:
        return ""

    extracted = trafilatura.extract(
        raw_content,
        output_format="markdown",
        target_language="zh",
        favor_precision=True,
        deduplicate=True,
    )
    if not extracted:
        return ""
    return normalize_content_text(extracted)


def _extract_with_readability(raw_content: str) -> str:
    try:
        from readability import Document
    except ImportError:
        return ""

    try:
        document = Document(raw_content)
        summary_html = document.summary(html_partial=True)
    except Exception:
        return ""
    return _html_to_text(summary_html)


def _extract_with_selectolax(raw_content: str) -> tuple[str, str]:
    try:
        from selectolax.parser import HTMLParser
    except ImportError:
        return raw_content, _fallback_strip_tags(raw_content)

    try:
        tree = HTMLParser(raw_content)
    except Exception:
        return raw_content, _fallback_strip_tags(raw_content)

    for selector in _DROP_SELECTORS:
        for node in tree.css(selector):
            node.decompose()

    for selector in _ARTICLE_SELECTORS:
        node = tree.css_first(selector)
        if node is None:
            continue
        text = normalize_content_text(node.text(separator=" "))
        if text:
            return tree.html, text

    text = ""
    if tree.body is not None:
        text = normalize_content_text(tree.body.text(separator=" "))
    if text:
        return tree.html, text
    return tree.html, _fallback_strip_tags(raw_content)


def _html_to_text(raw_content: str) -> str:
    _, text = _extract_with_selectolax(raw_content)
    if text:
        return text
    return _fallback_strip_tags(raw_content)


def _fallback_strip_tags(raw_content: str) -> str:
    stripped = _HTML_TAG_PATTERN.sub(" ", raw_content)
    return normalize_content_text(stripped)
