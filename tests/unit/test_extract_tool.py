from __future__ import annotations

import unittest

from app.domain.models import AcquiredContent
from app.tools.extract import extract_sources


class ExtractToolTest(unittest.TestCase):
    def test_extract_sources_preserves_provider_metadata_for_text_content(self) -> None:
        sources = extract_sources(
            [
                AcquiredContent(
                    url="https://example.com/research-worker",
                    title="Research worker",
                    content="Evidence scoring improves citation quality.",
                    content_format="text",
                    acquired_at="2026-04-13T00:00:00+00:00",
                    providers=["tavily", "brave"],
                    acquisition_method="provider_raw_content",
                    metadata={"provider_metadata": {"tavily": {"rank": 1}}},
                )
            ]
        )

        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].providers, ["tavily", "brave"])
        self.assertEqual(sources[0].acquisition_method, "provider_raw_content")
        self.assertEqual(sources[0].metadata["content_format"], "text")

    def test_extract_sources_strips_html_content(self) -> None:
        sources = extract_sources(
            [
                AcquiredContent(
                    url="https://example.com/html",
                    title="HTML page",
                    content="<html><body><p>Evidence scoring improved confidence.</p></body></html>",
                    content_format="html",
                    acquired_at="2026-04-13T00:00:00+00:00",
                    providers=["brave"],
                    acquisition_method="http_fetch",
                )
            ]
        )

        self.assertEqual(len(sources), 1)
        self.assertIn("Evidence scoring improved confidence.", sources[0].content)
        self.assertEqual(sources[0].acquisition_method, "http_fetch")
        self.assertTrue(sources[0].metadata["extractor"])

    def test_extract_sources_skips_block_pages(self) -> None:
        sources = extract_sources(
            [
                AcquiredContent(
                    url="https://example.com/wechat",
                    title="Blocked article",
                    content="<html><body><p>请在微信客户端打开链接并完成验证码验证</p></body></html>",
                    content_format="html",
                    acquired_at="2026-04-13T00:00:00+00:00",
                    providers=["brave"],
                    acquisition_method="http_fetch",
                )
            ]
        )

        self.assertEqual(sources, [])

    def test_extract_sources_reuses_cached_extracted_text_metadata(self) -> None:
        sources = extract_sources(
            [
                AcquiredContent(
                    url="https://example.com/cached",
                    title="Cached extraction",
                    content="<html><body><p>Raw HTML should not win.</p></body></html>",
                    content_format="html",
                    acquired_at="2026-04-13T00:00:00+00:00",
                    providers=["brave"],
                    acquisition_method="http_fetch",
                    metadata={
                        "extracted_text": "缓存后的正文内容更可靠。",
                        "extractor": "cached-trafilatura",
                    },
                )
            ]
        )

        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].content, "缓存后的正文内容更可靠。")
        self.assertEqual(sources[0].metadata["extractor"], "cached-trafilatura")


if __name__ == "__main__":
    unittest.main()
