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
            findings=[{"task_id": "task-1", "claim": "Fact", "source_id": "source-1"}],
            sources={"source-1": {"title": "Source", "url": "https://example.com"}},
            settings=self.settings,
            memory={
                "rolling_summary": "Earlier turns narrowed the scope to runtime memory.",
                "recent_turns": [],
                "key_facts": [],
                "open_questions": [],
            },
        )

        self.assertIn("## Conversation Context", report.markdown)
        self.assertIn("Not a citation source", report.markdown)


if __name__ == "__main__":
    unittest.main()
