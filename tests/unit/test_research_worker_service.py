from __future__ import annotations

import unittest

from app.domain.models import ResearchRequest, ResearchTask, SearchHit, SourceDocument
from app.services.research_worker import build_task_evidence, filter_pages, rank_search_hits, rewrite_queries


class ResearchWorkerServiceTest(unittest.TestCase):
    def setUp(self) -> None:
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
        queries = rewrite_queries(self.task, self.request)
        self.assertLessEqual(len(queries), 3)
        self.assertEqual(len(queries), len(set(query.casefold() for query in queries)))
        self.assertIn("Evidence scoring", queries[1])

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
                ),
            ],
            limit=2,
        )
        self.assertEqual(ranked[0].url, "https://example.com/research-worker")

    def test_filter_pages_drops_short_irrelevant_pages(self) -> None:
        pages = filter_pages(
            self.task,
            [
                {
                    "url": "https://example.com/short",
                    "title": "Short note",
                    "content": "tiny page",
                },
                {
                    "url": "https://example.com/relevant",
                    "title": "Research worker evidence scoring rollout",
                    "content": "Evidence scoring improves the research worker. " * 40,
                },
            ],
            limit=2,
        )
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0]["url"], "https://example.com/relevant")

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
                )
            ],
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(len(sources), 1)
        self.assertEqual(findings[0].source_id, "S1")
        self.assertGreater(findings[0].relevance_score, 0.2)
        self.assertGreater(findings[0].confidence, 0.3)
        self.assertIn("research worker evidence scoring rollout", findings[0].claim.casefold())


if __name__ == "__main__":
    unittest.main()
