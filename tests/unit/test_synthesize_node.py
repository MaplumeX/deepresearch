from __future__ import annotations

import unittest
from unittest.mock import patch

from app.config import Settings
from app.domain.models import StructuredReport
from app.graph.nodes.synthesize import synthesize_report_node


class SynthesizeNodeTest(unittest.TestCase):
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

    def test_synthesize_node_passes_coverage_requirements_to_service(self) -> None:
        state = {
            "request": {
                "question": "How should we evaluate deep research coverage?",
                "output_language": "en",
                "max_iterations": 2,
            },
            "tasks": [
                {
                    "task_id": "task-1",
                    "title": "Assess topic coverage",
                    "question": "Evaluate coverage quality.",
                    "coverage_tags": ["scope", "definitions"],
                }
            ],
            "coverage_requirements": [
                {
                    "requirement_id": "scope-terminology",
                    "title": "Scope and terminology",
                    "description": "Clarify scope and key terms.",
                    "coverage_tags": ["scope", "definitions"],
                }
            ],
            "findings": [],
            "sources": {},
            "warnings": [],
            "task_outcomes": [],
        }
        report = StructuredReport(
            title="Research Report",
            summary="",
            markdown="# Research Report",
            sections=[],
            cited_source_ids=[],
            citation_index=[],
            source_cards=[],
        )

        with patch("app.graph.nodes.synthesize.get_settings", return_value=self.settings), patch(
            "app.graph.nodes.synthesize.assign_report_headings",
            return_value=state["tasks"],
        ), patch(
            "app.graph.nodes.synthesize.synthesize_report",
            return_value=report,
        ) as mock_synthesize:
            result = synthesize_report_node(state)

        self.assertEqual(result["draft_report"], "# Research Report")
        self.assertEqual(
            mock_synthesize.call_args.kwargs["coverage_requirements"],
            state["coverage_requirements"],
        )


if __name__ == "__main__":
    unittest.main()
