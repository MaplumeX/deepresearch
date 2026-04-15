from __future__ import annotations

import unittest

from app.domain.models import AcquiredContent
from app.services.source_content import replace_contents, should_escalate_to_firecrawl, should_escalate_to_jina_reader


class SourceContentServiceTest(unittest.TestCase):
    def test_short_http_fetch_escalates_to_jina_then_firecrawl(self) -> None:
        content = AcquiredContent(
            url="https://example.com/news",
            title="News page",
            content="placeholder",
            content_format="html",
            acquired_at="2026-04-15T00:00:00+00:00",
            providers=["brave"],
            acquisition_method="http_fetch",
            metadata={"quality_failure_reason": "short_content"},
        )

        self.assertTrue(should_escalate_to_jina_reader(content))
        self.assertTrue(should_escalate_to_firecrawl(content))

    def test_snippet_content_does_not_escalate(self) -> None:
        content = AcquiredContent(
            url="https://example.com/snippet",
            title="Snippet page",
            content="short snippet",
            content_format="text",
            acquired_at="2026-04-15T00:00:00+00:00",
            providers=["brave"],
            acquisition_method="search_snippet",
            metadata={"quality_failure_reason": "short_content"},
        )

        self.assertFalse(should_escalate_to_jina_reader(content))
        self.assertFalse(should_escalate_to_firecrawl(content))

    def test_replace_contents_preserves_order(self) -> None:
        original = [
            AcquiredContent(
                url="https://example.com/a",
                title="A",
                content="old-a",
                content_format="text",
                acquired_at="2026-04-15T00:00:00+00:00",
                providers=[],
                acquisition_method="http_fetch",
            ),
            AcquiredContent(
                url="https://example.com/b",
                title="B",
                content="old-b",
                content_format="text",
                acquired_at="2026-04-15T00:00:00+00:00",
                providers=[],
                acquisition_method="http_fetch",
            ),
        ]
        replacement = AcquiredContent(
            url="https://example.com/b",
            title="B",
            content="new-b",
            content_format="markdown",
            acquired_at="2026-04-15T00:00:01+00:00",
            providers=[],
            acquisition_method="jina_reader",
        )

        merged = replace_contents(original, {replacement.url: replacement})

        self.assertEqual([item.url for item in merged], ["https://example.com/a", "https://example.com/b"])
        self.assertEqual(merged[1].content, "new-b")
        self.assertEqual(merged[1].acquisition_method, "jina_reader")


if __name__ == "__main__":
    unittest.main()
