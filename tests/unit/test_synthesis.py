from __future__ import annotations

import unittest

from app.config import Settings
from app.services.synthesis import synthesize_report


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


if __name__ == "__main__":
    unittest.main()
