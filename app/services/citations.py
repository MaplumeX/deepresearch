from __future__ import annotations

import re


CITATION_PATTERN = re.compile(r"\[(S[^\]]+)\]")


def extract_citation_ids(markdown: str) -> list[str]:
    return CITATION_PATTERN.findall(markdown)


def find_missing_citations(markdown: str, sources: dict[str, dict]) -> list[str]:
    citations = extract_citation_ids(markdown)
    return sorted({citation for citation in citations if citation not in sources})


def has_citations(markdown: str) -> bool:
    return bool(extract_citation_ids(markdown))

