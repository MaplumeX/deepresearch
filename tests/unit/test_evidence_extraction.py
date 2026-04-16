from __future__ import annotations

from dataclasses import replace
import unittest
from unittest.mock import patch

from app.config import Settings
from app.domain.models import Evidence, ResearchTask, SourceDocument
from app.services.evidence_extraction import build_task_evidence
from app.services.llm import LLMNotReadyError


class EvidenceExtractionServiceTest(unittest.TestCase):
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
        self.task = ResearchTask(
            task_id="task-1",
            title="Evidence extraction",
            question="Improve evidence extraction coverage for deep research",
        )
        self.source = SourceDocument(
            source_id="S1",
            url="https://docs.example.com/deep-research",
            title="Deep research rollout guide",
            content=(
                "Deep research is a workflow for collecting evidence across multiple sources. "
                "In one customer case, the workflow reduced citation errors by 32 percent. "
                "A key risk is that low-diversity sources can still pass naive evidence thresholds."
            ),
            fetched_at="2026-04-13T00:00:00+00:00",
            providers=["tavily"],
            acquisition_method="provider_raw_content",
        )

    def test_build_task_evidence_requires_llm(self) -> None:
        with self.assertRaises(LLMNotReadyError):
            build_task_evidence(
                self.task,
                [self.source],
                settings=replace(self.settings, llm_api_key=None, enable_llm_synthesis=False),
            )

    def test_build_task_evidence_keeps_sources_with_llm_extracted_evidence(self) -> None:
        with patch(
            "app.services.evidence_extraction._extract_source_evidence_with_llm",
            return_value=[
                Evidence(
                    evidence_id="",
                    task_id=self.task.task_id,
                    claim="The workflow reduced citation errors by 32 percent.",
                    snippet="The workflow reduced citation errors by 32 percent.",
                    source_id=self.source.source_id,
                    url=self.source.url,
                    title=self.source.title,
                    evidence_type="example",
                    source_role="official",
                )
            ],
        ):
            findings, sources = build_task_evidence(
                self.task,
                [self.source],
                settings=self.settings,
            )

        self.assertEqual(len(sources), 1)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].source_role, "official")
        self.assertEqual(findings[0].evidence_type, "example")
        self.assertEqual(findings[0].evidence_id, "task-1-S1-1")


if __name__ == "__main__":
    unittest.main()
