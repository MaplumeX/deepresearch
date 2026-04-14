from __future__ import annotations

import re
from collections import Counter
from typing import Any

from app.domain.models import (
    CitationIndexEntry,
    ReportDraft,
    ReportSection,
    SourceCard,
    StructuredReport,
)
from app.services.citations import extract_citation_ids


_HEADING_PATTERN = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_TITLE_PATTERN = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_SOURCES_HEADING = "sources"
_CONTEXT_HEADING = "conversation context"
_MAX_SNIPPET_LENGTH = 240


def build_structured_report(
    draft: ReportDraft,
    sources: dict[str, dict],
    findings: list[dict],
) -> StructuredReport:
    sections: list[ReportSection] = []
    if draft.summary.strip():
        sections.append(
            ReportSection(
                section_id="executive-summary",
                heading="Executive Summary",
                body_markdown=draft.summary.strip(),
                cited_source_ids=_extract_section_citations("Executive Summary", draft.summary),
            )
        )
    for index, section in enumerate(draft.sections, start=1):
        heading = section.heading.strip() or f"Section {index}"
        if _is_summary_heading(heading):
            continue
        body_markdown = section.body_markdown.strip()
        sections.append(
            ReportSection(
                section_id=_make_section_id(heading, index),
                heading=heading,
                body_markdown=body_markdown,
                cited_source_ids=_extract_section_citations(heading, body_markdown),
            )
        )

    cited_source_ids = _collect_cited_source_ids(sections)
    citation_index = _build_citation_index(sections, sources, findings)
    source_cards = _build_source_cards(cited_source_ids, sources, findings)
    markdown = render_structured_report_markdown(
        title=draft.title,
        summary=draft.summary,
        sections=sections,
        source_cards=source_cards,
    )
    return StructuredReport(
        title=draft.title,
        summary=draft.summary,
        markdown=markdown,
        sections=sections,
        cited_source_ids=cited_source_ids,
        citation_index=citation_index,
        source_cards=source_cards,
    )


def derive_structured_report(
    markdown: str,
    sources: dict[str, dict],
    findings: list[dict],
    title_hint: str = "Research Report",
) -> StructuredReport:
    normalized_markdown = markdown.strip()
    title = _extract_title(normalized_markdown) or title_hint
    sections = _parse_sections(normalized_markdown)
    summary = _extract_summary(normalized_markdown, sections)
    citation_index = _build_citation_index(sections, sources, findings)
    cited_source_ids = _collect_cited_source_ids(sections)
    source_cards = _build_source_cards(cited_source_ids, sources, findings)
    return StructuredReport(
        title=title,
        summary=summary,
        markdown=normalized_markdown,
        sections=sections,
        cited_source_ids=cited_source_ids,
        citation_index=citation_index,
        source_cards=source_cards,
    )


def render_structured_report_markdown(
    title: str,
    summary: str,
    sections: list[ReportSection],
    source_cards: list[SourceCard],
) -> str:
    blocks = [f"# {title}".strip()]
    summary_block = summary.strip()
    if summary_block:
        blocks.append("## Executive Summary\n" + summary_block)

    for section in sections:
        if _is_summary_heading(section.heading):
            continue
        body = section.body_markdown.strip()
        if not body:
            continue
        blocks.append(f"## {section.heading}\n{body}")

    source_lines = [
        f"- `{card.source_id}` [{card.title}]({card.url})"
        for card in source_cards
    ] or ["- No sources available."]
    blocks.append("## Sources\n" + "\n".join(source_lines))
    return "\n\n".join(block for block in blocks if block.strip())


def _build_citation_index(
    sections: list[ReportSection],
    sources: dict[str, dict],
    findings: list[dict],
) -> list[CitationIndexEntry]:
    source_ids = _collect_cited_source_ids(sections)
    if not source_ids:
        return []

    best_finding_by_source = _best_finding_by_source(findings)
    counts = Counter()
    sections_by_source: dict[str, set[str]] = {}
    for section in sections:
        if _is_non_evidence_section(section.heading):
            continue
        section_citations = extract_citation_ids(section.body_markdown)
        counts.update(section_citations)
        for source_id in section_citations:
            sections_by_source.setdefault(source_id, set()).add(section.section_id)

    entries: list[CitationIndexEntry] = []
    for source_id in source_ids:
        source = sources.get(source_id, {})
        finding = best_finding_by_source.get(source_id, {})
        entries.append(
            CitationIndexEntry(
                source_id=source_id,
                title=_as_text(source.get("title")) or source_id,
                url=_as_text(source.get("url")),
                snippet=_citation_snippet(source, finding),
                providers=_as_string_list(source.get("providers")),
                acquisition_method=_as_text(source.get("acquisition_method")) or None,
                cited_in_sections=sorted(sections_by_source.get(source_id, set())),
                occurrence_count=counts.get(source_id, 0),
                relevance_score=_as_optional_float(finding.get("relevance_score")),
                confidence=_as_optional_float(finding.get("confidence")),
            )
        )
    return entries


def _build_source_cards(
    cited_source_ids: list[str],
    sources: dict[str, dict],
    findings: list[dict],
) -> list[SourceCard]:
    best_finding_by_source = _best_finding_by_source(findings)
    cited_set = set(cited_source_ids)
    ordered_source_ids = cited_source_ids + [
        source_id for source_id in sorted(sources) if source_id not in cited_set
    ]
    cards: list[SourceCard] = []
    for source_id in ordered_source_ids:
        source = sources.get(source_id, {})
        finding = best_finding_by_source.get(source_id, {})
        cards.append(
            SourceCard(
                source_id=source_id,
                title=_as_text(source.get("title")) or source_id,
                url=_as_text(source.get("url")),
                snippet=_citation_snippet(source, finding),
                providers=_as_string_list(source.get("providers")),
                acquisition_method=_as_text(source.get("acquisition_method")) or None,
                fetched_at=_as_text(source.get("fetched_at")),
                is_cited=source_id in cited_set,
            )
        )
    return cards


def _best_finding_by_source(findings: list[dict]) -> dict[str, dict]:
    best: dict[str, dict] = {}
    for finding in findings:
        source_id = _as_text(finding.get("source_id"))
        if not source_id:
            continue
        current = best.get(source_id)
        if current is None or _finding_rank(finding) > _finding_rank(current):
            best[source_id] = finding
    return best


def _finding_rank(finding: dict[str, Any]) -> tuple[float, float]:
    return (
        _as_optional_float(finding.get("confidence")) or 0.0,
        _as_optional_float(finding.get("relevance_score")) or 0.0,
    )


def _citation_snippet(source: dict, finding: dict) -> str:
    finding_snippet = _trim_text(_as_text(finding.get("snippet")))
    if finding_snippet:
        return finding_snippet
    claim = _trim_text(_as_text(finding.get("claim")))
    if claim:
        return claim
    content = _trim_text(_as_text(source.get("content")))
    if content:
        return content
    return _as_text(source.get("title"))


def _parse_sections(markdown: str) -> list[ReportSection]:
    if not markdown:
        return []

    matches = list(_HEADING_PATTERN.finditer(markdown))
    if not matches:
        body = _strip_title(markdown).strip()
        if not body:
            return []
        return [
            ReportSection(
                section_id="report-body",
                heading="Report",
                body_markdown=body,
                cited_source_ids=_extract_section_citations("Report", body),
            )
        ]

    sections: list[ReportSection] = []
    for index, match in enumerate(matches, start=1):
        start = match.end()
        end = matches[index].start() if index < len(matches) else len(markdown)
        heading = match.group(1).strip() or f"Section {index}"
        body = markdown[start:end].strip()
        sections.append(
            ReportSection(
                section_id=_make_section_id(heading, index),
                heading=heading,
                body_markdown=body,
                cited_source_ids=_extract_section_citations(heading, body),
            )
        )
    return sections


def _extract_title(markdown: str) -> str:
    match = _TITLE_PATTERN.search(markdown)
    if match:
        return match.group(1).strip()
    return ""


def _strip_title(markdown: str) -> str:
    return _TITLE_PATTERN.sub("", markdown, count=1).strip()


def _extract_summary(markdown: str, sections: list[ReportSection]) -> str:
    for section in sections:
        if _is_summary_heading(section.heading):
            return section.body_markdown

    body = _strip_title(markdown)
    if not body:
        return ""

    if "##" in body:
        return body.split("##", 1)[0].strip()
    return body


def _collect_cited_source_ids(sections: list[ReportSection]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for section in sections:
        if _is_non_evidence_section(section.heading):
            continue
        for source_id in section.cited_source_ids:
            if source_id in seen:
                continue
            seen.add(source_id)
            ordered.append(source_id)
    return ordered


def _extract_section_citations(heading: str, body_markdown: str) -> list[str]:
    if _is_non_evidence_section(heading):
        return []
    citations = extract_citation_ids(body_markdown)
    seen: set[str] = set()
    ordered: list[str] = []
    for source_id in citations:
        if source_id in seen:
            continue
        seen.add(source_id)
        ordered.append(source_id)
    return ordered


def _is_non_evidence_section(heading: str) -> bool:
    normalized = heading.strip().casefold()
    return normalized in {_SOURCES_HEADING, _CONTEXT_HEADING}


def _is_summary_heading(heading: str) -> bool:
    return heading.strip().casefold() == "executive summary"


def _make_section_id(heading: str, index: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", heading.casefold()).strip("-")
    if not slug:
        slug = f"section-{index}"
    return slug


def _trim_text(text: str) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= _MAX_SNIPPET_LENGTH:
        return normalized
    return normalized[: _MAX_SNIPPET_LENGTH - 1].rstrip() + "…"


def _as_text(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _as_optional_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None
