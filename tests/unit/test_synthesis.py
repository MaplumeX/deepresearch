from __future__ import annotations

import unittest
from unittest.mock import patch

from app.config import Settings
from app.domain.models import ReportDraft, ReportSectionDraft
from app.services.synthesis import _build_compact_payload, synthesize_report


class SynthesisServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            app_name="test",
            planner_model="test-model",
            synthesis_model="test-model",
            llm_api_key=None,
            llm_base_url=None,
            tavily_api_key=None,
            brave_api_key=None,
            checkpoint_db_path="test.db",
            runs_db_path="test-runs.db",
            fetch_timeout_seconds=1.0,
            default_max_iterations=2,
            default_max_parallel_tasks=3,
            search_max_results=3,
            require_human_review=False,
            enable_llm_planning=False,
            enable_llm_synthesis=False,
        )

    def test_fallback_synthesis_includes_memory_context_section(self) -> None:
        report = synthesize_report(
            question="Can you continue this analysis?",
            tasks=[{"task_id": "task-1", "title": "Topic"}],
            findings=[
                {
                    "task_id": "task-1",
                    "claim": "Fact",
                    "snippet": "Fact",
                    "source_id": "Ssource001",
                    "confidence": 0.8,
                    "relevance_score": 0.7,
                }
            ],
            sources={
                "Ssource001": {
                    "title": "Source",
                    "url": "https://example.com",
                    "content": "Fact",
                    "providers": ["tavily"],
                    "acquisition_method": "http_fetch",
                    "fetched_at": "2026-04-14T08:00:00+00:00",
                }
            },
            settings=self.settings,
            memory={
                "rolling_summary": "Earlier turns narrowed the scope to runtime memory.",
                "recent_turns": [],
                "key_facts": [],
                "open_questions": [],
            },
        )

        self.assertEqual(report.title, "Research Report")
        self.assertIn("## Conversation Context", report.markdown)
        self.assertIn("Not a citation source", report.markdown)
        self.assertEqual(report.cited_source_ids, ["Ssource001"])
        self.assertEqual(report.citation_index[0].source_id, "Ssource001")
        self.assertEqual(report.source_cards[0].source_id, "Ssource001")
        self.assertEqual(report.sections[0].heading, "Executive Summary")
        self.assertEqual(report.sections[1].heading, "Conversation Context")
        self.assertEqual(report.sections[2].heading, "Key Findings")

    def test_fallback_synthesis_groups_examples_and_risks(self) -> None:
        report = synthesize_report(
            question="How should we evaluate deep research coverage?",
            tasks=[{"task_id": "task-1", "title": "Coverage"}],
            findings=[
                {
                    "task_id": "task-1",
                    "claim": "A case study reduced citation errors by 32 percent.",
                    "snippet": "A case study reduced citation errors by 32 percent.",
                    "source_id": "Sexample",
                    "evidence_type": "example",
                    "confidence": 0.8,
                    "relevance_score": 0.7,
                },
                {
                    "task_id": "task-1",
                    "claim": "Low-diversity sources can still bias the report.",
                    "snippet": "Low-diversity sources can still bias the report.",
                    "source_id": "Srisk",
                    "evidence_type": "risk",
                    "confidence": 0.8,
                    "relevance_score": 0.7,
                },
            ],
            sources={
                "Sexample": {
                    "title": "Example",
                    "url": "https://example.com/example",
                    "content": "A case study reduced citation errors by 32 percent.",
                    "providers": ["tavily"],
                    "acquisition_method": "http_fetch",
                    "fetched_at": "2026-04-14T08:00:00+00:00",
                },
                "Srisk": {
                    "title": "Risk",
                    "url": "https://example.com/risk",
                    "content": "Low-diversity sources can still bias the report.",
                    "providers": ["tavily"],
                    "acquisition_method": "http_fetch",
                    "fetched_at": "2026-04-14T08:00:00+00:00",
                },
            },
            settings=self.settings,
            memory=None,
        )

        headings = [section.heading for section in report.sections]
        self.assertIn("Evidence and Examples", headings)
        self.assertIn("Risks and Limitations", headings)

    def test_compact_payload_excludes_raw_source_content(self) -> None:
        payload = _build_compact_payload(
            question="How should we evaluate deep research coverage?",
            tasks=[{"task_id": "task-1", "title": "Coverage", "question": "Evaluate coverage"}],
            findings=[
                {
                    "task_id": "task-1",
                    "claim": "A case study reduced citation errors by 32 percent.",
                    "snippet": "A case study reduced citation errors by 32 percent.",
                    "source_id": "Sexample",
                    "evidence_type": "example",
                    "confidence": 0.8,
                    "relevance_score": 0.7,
                    "title": "Example",
                    "url": "https://example.com/example",
                }
            ],
            sources={
                "Sexample": {
                    "title": "Example",
                    "url": "https://example.com/example",
                    "content": "Full source content should stay out of synthesis payloads.",
                    "providers": ["tavily"],
                }
            },
            memory_brief="None",
        )

        self.assertIn("Sexample", payload.sources)
        self.assertNotIn("content", payload.sources["Sexample"])
        self.assertIn("snippet", payload.sources["Sexample"])

    def test_synthesis_uses_multi_stage_when_payload_exceeds_soft_limit(self) -> None:
        llm_settings = Settings(
            app_name="test",
            planner_model="test-model",
            synthesis_model="test-model",
            llm_api_key="dummy-key",
            llm_base_url=None,
            tavily_api_key=None,
            brave_api_key=None,
            checkpoint_db_path="test.db",
            runs_db_path="test-runs.db",
            fetch_timeout_seconds=1.0,
            default_max_iterations=2,
            default_max_parallel_tasks=3,
            search_max_results=3,
            require_human_review=False,
            enable_llm_planning=False,
            enable_llm_synthesis=True,
            synthesis_soft_char_limit=10,
            synthesis_hard_char_limit=1000,
        )
        staged_draft = ReportDraft(
            title="Research Report",
            summary="- Fact [Ssource001]",
            sections=[
                ReportSectionDraft(
                    heading="Key Findings",
                    body_markdown="- Fact [Ssource001]",
                )
            ],
        )

        with patch("app.services.synthesis._maybe_synthesize_single_call") as mock_single, patch(
            "app.services.synthesis._maybe_synthesize_multi_stage",
            return_value=staged_draft,
        ) as mock_multi:
            report = synthesize_report(
                question="Can you continue this analysis?",
                tasks=[{"task_id": "task-1", "title": "Topic", "question": "Continue the analysis"}],
                findings=[
                    {
                        "task_id": "task-1",
                        "claim": "Fact",
                        "snippet": "Fact",
                        "source_id": "Ssource001",
                        "confidence": 0.8,
                        "relevance_score": 0.7,
                    }
                ],
                sources={
                    "Ssource001": {
                        "title": "Source",
                        "url": "https://example.com",
                        "content": "Fact",
                        "providers": ["tavily"],
                        "acquisition_method": "http_fetch",
                        "fetched_at": "2026-04-14T08:00:00+00:00",
                    }
                },
                settings=llm_settings,
                memory=None,
            )

        mock_single.assert_not_called()
        mock_multi.assert_called_once()
        self.assertIn("## Key Findings", report.markdown)


if __name__ == "__main__":
    unittest.main()
