from __future__ import annotations

import unittest

from app.graph.nodes.audit import citation_audit


class CitationAuditTest(unittest.TestCase):
    def test_requires_review_when_structured_section_has_no_citations(self) -> None:
        state = {
            "draft_report": "# Research Report\n\n## Executive Summary\n- Fact [Sabc12345]\n\n## Analysis\nPlain conclusion without sources.",
            "draft_structured_report": {
                "title": "Research Report",
                "summary": "- Fact [Sabc12345]",
                "markdown": "# Research Report\n\n## Executive Summary\n- Fact [Sabc12345]\n\n## Analysis\nPlain conclusion without sources.",
                "sections": [
                    {
                        "section_id": "executive-summary",
                        "heading": "Executive Summary",
                        "body_markdown": "- Fact [Sabc12345]",
                        "cited_source_ids": ["Sabc12345"],
                    },
                    {
                        "section_id": "analysis",
                        "heading": "Analysis",
                        "body_markdown": "Plain conclusion without sources.",
                        "cited_source_ids": [],
                    },
                ],
                "cited_source_ids": ["Sabc12345"],
                "citation_index": [
                    {
                        "source_id": "Sabc12345",
                        "title": "Known",
                        "url": "https://example.com",
                        "snippet": "Fact",
                        "providers": ["tavily"],
                        "acquisition_method": "http_fetch",
                        "cited_in_sections": ["executive-summary"],
                        "occurrence_count": 1,
                        "relevance_score": 0.7,
                        "confidence": 0.8,
                    }
                ],
                "source_cards": [
                    {
                        "source_id": "Sabc12345",
                        "title": "Known",
                        "url": "https://example.com",
                        "snippet": "Fact",
                        "providers": ["tavily"],
                        "acquisition_method": "http_fetch",
                        "fetched_at": "2026-04-14T08:00:00+00:00",
                        "is_cited": True,
                    }
                ],
            },
            "sources": {
                "Sabc12345": {
                    "title": "Known",
                    "url": "https://example.com",
                }
            },
            "findings": [
                {
                    "task_id": "task-1",
                    "claim": "Fact",
                    "source_id": "Sabc12345",
                }
            ],
            "quality_gate": {},
            "warnings": [],
            "review_required": False,
        }

        result = citation_audit(state)

        self.assertTrue(result["review_required"])
        self.assertIn("Section 'Analysis' does not include inline citations.", result["warnings"])


if __name__ == "__main__":
    unittest.main()
