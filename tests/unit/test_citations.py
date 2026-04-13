from __future__ import annotations

import unittest

from app.services.citations import extract_citation_ids, find_missing_citations, has_citations


class CitationServiceTest(unittest.TestCase):
    def test_extracts_inline_citations(self) -> None:
        markdown = "Line one [Sabc12345] and line two [Sdef67890]."
        self.assertEqual(extract_citation_ids(markdown), ["Sabc12345", "Sdef67890"])

    def test_detects_missing_citations(self) -> None:
        markdown = "Known [Sabc12345], unknown [Sdef67890]."
        sources = {"Sabc12345": {"title": "Known"}}
        self.assertEqual(find_missing_citations(markdown, sources), ["Sdef67890"])

    def test_reports_presence_of_citations(self) -> None:
        self.assertTrue(has_citations("Result [Sabc12345]"))
        self.assertFalse(has_citations("Result without sources"))


if __name__ == "__main__":
    unittest.main()

