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


if __name__ == "__main__":
    unittest.main()
