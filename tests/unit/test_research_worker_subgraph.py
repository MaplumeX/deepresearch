from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, Mock, patch

from app.config import Settings
from app.domain.models import AcquiredContent
from app.graph.subgraphs import research_worker as worker_module


class ResearchWorkerSubgraphTest(unittest.IsolatedAsyncioTestCase):
    def _settings(self, **overrides) -> Settings:
        return Settings(
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
            **overrides,
        )

    def _state(self) -> dict:
        return {
            "request": {
                "question": "如何改进证据抽取？",
                "scope": "关注中文新闻站",
                "output_language": "zh-CN",
                "max_iterations": 2,
                "max_parallel_tasks": 3,
            },
            "task": {
                "task_id": "task-1",
                "title": "中文新闻抓取",
                "question": "如何提高中文新闻抓取质量？",
                "status": "pending",
            },
            "search_hits": [
                {
                    "title": "Example",
                    "url": "https://example.com/news",
                    "snippet": "news snippet",
                    "providers": ["brave"],
                    "provider_metadata": {"brave": {"rank": 1}},
                }
            ],
        }

    async def test_acquire_and_filter_node_uses_jina_before_firecrawl(self) -> None:
        initial = AcquiredContent(
            url="https://example.com/news",
            title="Example",
            content="placeholder",
            content_format="html",
            acquired_at="2026-04-15T00:00:00+00:00",
            providers=["brave"],
            acquisition_method="http_fetch",
            metadata={"quality_failure_reason": "short_content"},
        )
        upgraded = AcquiredContent(
            url="https://example.com/news",
            title="Example",
            content="这是一段足够长的中文正文。" * 20,
            content_format="markdown",
            acquired_at="2026-04-15T00:00:01+00:00",
            providers=["brave"],
            acquisition_method="jina_reader",
            metadata={"extracted_text": "这是一段足够长的中文正文。" * 20},
        )
        settings = self._settings(enable_jina_reader_fallback=True, enable_firecrawl_fallback=True)

        with (
            patch.object(worker_module, "get_settings", return_value=settings),
            patch.object(worker_module, "acquire_contents", new=AsyncMock(return_value=[initial])),
            patch.object(worker_module, "fetch_with_jina_reader", new=AsyncMock(return_value={upgraded.url: upgraded})) as jina_mock,
            patch.object(worker_module, "fetch_with_firecrawl", new=AsyncMock(return_value={})) as firecrawl_mock,
            patch.object(worker_module, "filter_acquired_contents", new=Mock(side_effect=lambda task, contents, limit: contents)),
        ):
            result = await worker_module.acquire_and_filter_node(self._state())

        self.assertEqual(len(result["acquired_contents"]), 1)
        self.assertEqual(result["acquired_contents"][0]["acquisition_method"], "jina_reader")
        jina_mock.assert_awaited_once()
        firecrawl_mock.assert_awaited_once()
        self.assertEqual(firecrawl_mock.await_args.args[0], [])

    async def test_acquire_and_filter_node_uses_firecrawl_after_jina_failure(self) -> None:
        initial = AcquiredContent(
            url="https://example.com/news",
            title="Example",
            content="placeholder",
            content_format="html",
            acquired_at="2026-04-15T00:00:00+00:00",
            providers=["brave"],
            acquisition_method="http_fetch",
            metadata={"quality_failure_reason": "short_content"},
        )
        jina_failed = AcquiredContent(
            url="https://example.com/news",
            title="Example",
            content="请在微信客户端打开链接并完成验证码验证",
            content_format="markdown",
            acquired_at="2026-04-15T00:00:01+00:00",
            providers=["brave"],
            acquisition_method="jina_reader",
            metadata={
                "extracted_text": "请在微信客户端打开链接并完成验证码验证",
                "quality_failure_reason": "blocked_page",
            },
        )
        firecrawl_upgraded = AcquiredContent(
            url="https://example.com/news",
            title="Example",
            content="Firecrawl 提供的完整正文。" * 20,
            content_format="markdown",
            acquired_at="2026-04-15T00:00:02+00:00",
            providers=["brave"],
            acquisition_method="firecrawl_scrape",
            metadata={"extracted_text": "Firecrawl 提供的完整正文。" * 20},
        )
        settings = self._settings(enable_jina_reader_fallback=True, enable_firecrawl_fallback=True, firecrawl_api_key="firecrawl-key")

        with (
            patch.object(worker_module, "get_settings", return_value=settings),
            patch.object(worker_module, "acquire_contents", new=AsyncMock(return_value=[initial])),
            patch.object(worker_module, "fetch_with_jina_reader", new=AsyncMock(return_value={jina_failed.url: jina_failed})) as jina_mock,
            patch.object(worker_module, "fetch_with_firecrawl", new=AsyncMock(return_value={firecrawl_upgraded.url: firecrawl_upgraded})) as firecrawl_mock,
            patch.object(worker_module, "filter_acquired_contents", new=Mock(side_effect=lambda task, contents, limit: contents)),
        ):
            result = await worker_module.acquire_and_filter_node(self._state())

        self.assertEqual(result["acquired_contents"][0]["acquisition_method"], "firecrawl_scrape")
        jina_mock.assert_awaited_once()
        firecrawl_mock.assert_awaited_once()
        self.assertEqual(firecrawl_mock.await_args.args[0][0].acquisition_method, "jina_reader")


if __name__ == "__main__":
    unittest.main()
