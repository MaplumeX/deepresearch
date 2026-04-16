from __future__ import annotations

from dataclasses import replace
import unittest
from unittest.mock import patch

from app.config import Settings
from app.domain.models import ReportDraft, ReportSectionDraft
from app.services.llm import InsufficientEvidenceError, LLMInvocationError, LLMOutputInvalidError
from app.services.synthesis import _build_compact_payload, assign_report_headings, synthesize_report


class SynthesisServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            app_name="test",
            planner_model="test-model",
            synthesis_model="test-model",
            llm_api_key="dummy-key",
            llm_base_url=None,
            tavily_api_key=None,
            brave_api_key=None,
            serper_api_key=None,
            checkpoint_db_path="test.db",
            runs_db_path="test-runs.db",
            fetch_timeout_seconds=1.0,
            default_max_iterations=2,
            default_max_parallel_tasks=3,
            search_max_results=3,
            require_human_review=False,
            enable_llm_planning=False,
            enable_llm_synthesis=True,
        )
        self.tasks = [
            {
                "task_id": "task-1",
                "title": "Assess topic coverage",
                "report_heading": "Coverage quality",
                "question": "Continue the analysis",
            }
        ]
        self.findings = [
            {
                "task_id": "task-1",
                "claim": "Fact",
                "snippet": "Fact",
                "source_id": "Ssource001",
                "confidence": 0.8,
                "relevance_score": 0.7,
            }
        ]
        self.sources = {
            "Ssource001": {
                "title": "Source",
                "url": "https://example.com",
                "content": "Fact",
                "providers": ["tavily"],
                "acquisition_method": "http_fetch",
                "fetched_at": "2026-04-14T08:00:00+00:00",
            }
        }

    def test_synthesis_requires_findings(self) -> None:
        with self.assertRaises(InsufficientEvidenceError):
            synthesize_report(
                question="Can you continue this analysis?",
                tasks=self.tasks,
                findings=[],
                sources=self.sources,
                settings=self.settings,
                output_language="en",
            )

    def test_compact_payload_excludes_raw_source_content(self) -> None:
        payload = _build_compact_payload(
            question="How should we evaluate deep research coverage?",
            tasks=self.tasks,
            coverage_requirements=[],
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

    def test_assign_report_headings_uses_llm_output(self) -> None:
        with patch(
            "app.services.synthesis._generate_report_headings_with_llm",
            return_value={"task-1": "Coverage quality"},
        ):
            tasks = assign_report_headings(
                question="请继续分析这个问题",
                tasks=[
                    {
                        "task_id": "task-1",
                        "title": "评估研究覆盖质量",
                        "question": "请评估研究覆盖质量。",
                    }
                ],
                findings=[],
                settings=self.settings,
                output_language="zh-CN",
            )

        self.assertEqual(tasks[0]["title"], "评估研究覆盖质量")
        self.assertEqual(tasks[0]["report_heading"], "Coverage quality")

    def test_assign_report_headings_rejects_duplicate_llm_output(self) -> None:
        with patch(
            "app.services.synthesis._generate_report_headings_with_llm",
            return_value={
                "task-1": "Coverage quality",
                "task-2": "Coverage quality",
            },
        ):
            with self.assertRaises(LLMOutputInvalidError):
                assign_report_headings(
                    question="How should we evaluate deep research coverage?",
                    tasks=[
                        {
                            "task_id": "task-1",
                            "title": "Assess coverage quality",
                            "question": "Evaluate coverage quality.",
                        },
                        {
                            "task_id": "task-2",
                            "title": "Assess evidence gaps",
                            "question": "Evaluate evidence gaps.",
                        },
                    ],
                    findings=[],
                    settings=self.settings,
                    output_language="en",
                )

    def test_synthesis_uses_multi_stage_when_payload_exceeds_soft_limit(self) -> None:
        llm_settings = replace(self.settings, synthesis_soft_char_limit=10, synthesis_hard_char_limit=1000)
        staged_draft = ReportDraft(
            title="Research Report",
            summary="- Fact [Ssource001]",
            sections=[
                ReportSectionDraft(
                    heading="Coverage quality",
                    body_markdown="- Fact [Ssource001]",
                ),
                ReportSectionDraft(
                    heading="Conclusion",
                    body_markdown="- Fact [Ssource001]",
                ),
            ],
        )

        with patch("app.services.synthesis._maybe_synthesize_single_call") as mock_single, patch(
            "app.services.synthesis._maybe_synthesize_multi_stage",
            return_value=staged_draft,
        ) as mock_multi:
            report = synthesize_report(
                question="Can you continue this analysis?",
                tasks=self.tasks,
                findings=self.findings,
                sources=self.sources,
                settings=llm_settings,
                memory=None,
                output_language="en",
            )

        mock_single.assert_not_called()
        mock_multi.assert_called_once()
        self.assertIn("## Summary", report.markdown)
        self.assertIn("## Coverage quality", report.markdown)
        self.assertIn("## Conclusion", report.markdown)

    def test_synthesis_falls_back_to_multi_stage_llm_when_single_call_fails(self) -> None:
        staged_draft = ReportDraft(
            title="Research Report",
            summary="- Fact [Ssource001]",
            sections=[
                ReportSectionDraft(
                    heading="Coverage quality",
                    body_markdown="- Fact [Ssource001]",
                ),
                ReportSectionDraft(
                    heading="Conclusion",
                    body_markdown="- Fact [Ssource001]",
                ),
            ],
        )

        with patch(
            "app.services.synthesis._maybe_synthesize_single_call",
            side_effect=LLMInvocationError("single call failed"),
        ) as mock_single, patch(
            "app.services.synthesis._maybe_synthesize_multi_stage",
            return_value=staged_draft,
        ) as mock_multi:
            report = synthesize_report(
                question="Can you continue this analysis?",
                tasks=self.tasks,
                findings=self.findings,
                sources=self.sources,
                settings=self.settings,
                memory=None,
                output_language="en",
            )

        mock_single.assert_called_once()
        mock_multi.assert_called_once()
        self.assertIn("## Coverage quality", report.markdown)


if __name__ == "__main__":
    unittest.main()
