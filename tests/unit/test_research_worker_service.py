from __future__ import annotations

import unittest

from app.config import Settings
from app.domain.models import AcquiredContent, ResearchRequest, ResearchTask, SearchHit, SourceDocument
from app.services.research_worker import build_task_evidence, filter_acquired_contents, rank_search_hits, rewrite_queries


class ResearchWorkerServiceTest(unittest.TestCase):
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
        self.request = ResearchRequest(
            question="How should we upgrade the research worker?",
            scope="Focus on query rewriting and evidence scoring",
            output_language="en",
        )
        self.task = ResearchTask(
            task_id="task-1",
            title="Evidence scoring",
            question="Upgrade the research worker evidence scoring pipeline",
        )

    def test_rewrite_queries_deduplicates_and_limits_results(self) -> None:
        queries = rewrite_queries(self.task, self.request, settings=self.settings)
        self.assertLessEqual(len(queries), 6)
        self.assertEqual(len(queries), len(set(query.casefold() for query in queries)))
        self.assertTrue(any("evidence scoring" in query.casefold() for query in queries))
        self.assertTrue(any("official" in query.casefold() for query in queries))

    def test_rank_search_hits_prefers_relevant_titles(self) -> None:
        ranked = rank_search_hits(
            self.task,
            [
                SearchHit(
                    title="Generic homepage",
                    url="https://example.com",
                    snippet="Welcome to our site",
                ),
                SearchHit(
                    title="Research worker evidence scoring design",
                    url="https://example.com/research-worker",
                    snippet="Evidence scoring improves confidence and relevance.",
                    providers=["tavily", "brave"],
                    provider_metadata={
                        "tavily": {"rank": 1},
                        "brave": {"rank": 2},
                    },
                ),
            ],
            limit=2,
        )
        self.assertEqual(ranked[0].url, "https://example.com/research-worker")
        self.assertEqual(ranked[0].providers, ["brave", "tavily"])

    def test_rank_search_hits_merges_cross_provider_duplicates(self) -> None:
        ranked = rank_search_hits(
            self.task,
            [
                SearchHit(
                    title="Evidence scoring design",
                    url="https://example.com/research-worker",
                    snippet="Short summary",
                    providers=["tavily"],
                    provider_metadata={"tavily": {"rank": 1}},
                    raw_content="Provider raw content about evidence scoring." * 10,
                    raw_content_format="text",
                ),
                SearchHit(
                    title="Research worker evidence scoring design",
                    url="https://example.com/research-worker",
                    snippet="Longer cross-provider summary for the same document.",
                    providers=["brave"],
                    provider_metadata={"brave": {"rank": 2}},
                ),
            ],
            limit=3,
        )
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0].providers, ["brave", "tavily"])
        self.assertIsNotNone(ranked[0].raw_content)

    def test_filter_acquired_contents_drops_short_irrelevant_pages(self) -> None:
        contents = filter_acquired_contents(
            self.task,
            [
                AcquiredContent(
                    url="https://example.com/short",
                    title="Short note",
                    content="tiny page",
                    content_format="text",
                    acquired_at="2026-04-13T00:00:00+00:00",
                    providers=["brave"],
                    acquisition_method="search_snippet",
                ),
                AcquiredContent(
                    url="https://example.com/relevant",
                    title="Research worker evidence scoring rollout",
                    content="Evidence scoring improves the research worker. " * 40,
                    content_format="text",
                    acquired_at="2026-04-13T00:00:00+00:00",
                    providers=["tavily", "brave"],
                    acquisition_method="provider_raw_content",
                ),
            ],
            limit=2,
        )
        self.assertEqual(len(contents), 1)
        self.assertEqual(contents[0].url, "https://example.com/relevant")

    def test_filter_acquired_contents_uses_extracted_text_metadata(self) -> None:
        contents = filter_acquired_contents(
            self.task,
            [
                AcquiredContent(
                    url="https://example.com/raw-noisy",
                    title="Research worker evidence scoring rollout",
                    content="<html>" + ("noise " * 200) + "</html>",
                    content_format="html",
                    acquired_at="2026-04-13T00:00:00+00:00",
                    providers=["brave"],
                    acquisition_method="http_fetch",
                    metadata={"extracted_text": "简短摘要"},
                ),
                AcquiredContent(
                    url="https://example.com/relevant",
                    title="Research worker evidence scoring rollout",
                    content="Evidence scoring improves the research worker. " * 40,
                    content_format="text",
                    acquired_at="2026-04-13T00:00:00+00:00",
                    providers=["tavily"],
                    acquisition_method="provider_raw_content",
                ),
            ],
            limit=2,
        )

        self.assertEqual(len(contents), 1)
        self.assertEqual(contents[0].url, "https://example.com/relevant")

    def test_filter_acquired_contents_skips_blocked_pages_even_in_fallback(self) -> None:
        contents = filter_acquired_contents(
            self.task,
            [
                AcquiredContent(
                    url="https://example.com/blocked",
                    title="Blocked page",
                    content="<html>" + ("placeholder " * 200) + "</html>",
                    content_format="html",
                    acquired_at="2026-04-13T00:00:00+00:00",
                    providers=["brave"],
                    acquisition_method="http_fetch",
                    metadata={
                        "extracted_text": "请在微信客户端打开链接并完成验证码验证",
                        "quality_failure_reason": "blocked_page",
                    },
                )
            ],
            limit=1,
        )

        self.assertEqual(contents, [])

    def test_build_task_evidence_scores_relevant_sources(self) -> None:
        findings, sources = build_task_evidence(
            self.task,
            [
                SourceDocument(
                    source_id="S1",
                    url="https://example.com/research-worker",
                    title="Research worker evidence scoring rollout",
                    content=(
                        "The research worker evidence scoring rollout improved confidence by 25 percent "
                        "and reduced weak citations across the report."
                    ),
                    fetched_at="2026-04-13T00:00:00+00:00",
                    providers=["tavily", "brave"],
                    acquisition_method="provider_raw_content",
                )
            ],
            settings=self.settings,
        )
        self.assertGreaterEqual(len(findings), 1)
        self.assertEqual(len(sources), 1)
        self.assertEqual(findings[0].source_id, "S1")
        self.assertGreater(findings[0].relevance_score, 0.2)
        self.assertGreater(findings[0].confidence, 0.3)
        self.assertIn("research worker evidence scoring rollout", findings[0].claim.casefold())
        self.assertIn(findings[0].evidence_type, {"fact", "statistic", "example"})


if __name__ == "__main__":
    unittest.main()
