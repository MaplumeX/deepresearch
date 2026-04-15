from __future__ import annotations

import unittest

from app.config import Settings
from app.domain.models import ResearchTask, SourceDocument
from app.services.evidence_extraction import build_task_evidence


class EvidenceExtractionServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            app_name="test",
            planner_model="test-model",
            synthesis_model="test-model",
            llm_api_key=None,
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
            enable_llm_synthesis=False,
        )
        self.task = ResearchTask(
            task_id="task-1",
            title="Evidence extraction",
            question="Improve evidence extraction coverage for deep research",
        )

    def test_fallback_extraction_keeps_multiple_supported_evidence_items(self) -> None:
        findings, sources = build_task_evidence(
            self.task,
            [
                SourceDocument(
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
            ],
            settings=self.settings,
        )

        self.assertEqual(len(sources), 1)
        self.assertGreaterEqual(len(findings), 2)
        self.assertTrue(all(finding.snippet in sources[0].content for finding in findings))
        self.assertIn("official", {finding.source_role for finding in findings})
        self.assertTrue({"example", "risk"} & {finding.evidence_type for finding in findings})


if __name__ == "__main__":
    unittest.main()
