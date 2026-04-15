from __future__ import annotations

import unittest

from app.config import Settings
from app.domain.models import SearchHit
from app.tools import search as search_module


class SearchToolTest(unittest.TestCase):
    def _settings(self, **overrides) -> Settings:
        defaults = {
            "app_name": "test",
            "planner_model": "test-model",
            "synthesis_model": "test-model",
            "llm_api_key": None,
            "llm_base_url": None,
            "tavily_api_key": None,
            "brave_api_key": None,
            "serper_api_key": None,
            "checkpoint_db_path": "test.db",
            "runs_db_path": "test-runs.db",
            "fetch_timeout_seconds": 1.0,
            "default_max_iterations": 2,
            "default_max_parallel_tasks": 3,
            "search_max_results": 3,
            "require_human_review": False,
            "enable_llm_planning": False,
            "enable_llm_synthesis": False,
        }
        defaults.update(overrides)
        return Settings(**defaults)

    def test_build_providers_empty_when_no_keys(self) -> None:
        settings = self._settings()
        providers = search_module._build_providers(settings)
        self.assertEqual(len(providers), 0)

    def test_build_providers_includes_tavily(self) -> None:
        settings = self._settings(tavily_api_key="tavily-key")
        providers = search_module._build_providers(settings)
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0].name, "tavily")

    def test_build_providers_includes_brave(self) -> None:
        settings = self._settings(brave_api_key="brave-key")
        providers = search_module._build_providers(settings)
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0].name, "brave")

    def test_build_providers_includes_serper(self) -> None:
        settings = self._settings(serper_api_key="serper-key")
        providers = search_module._build_providers(settings)
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0].name, "serper")

    def test_build_providers_includes_all_configured(self) -> None:
        settings = self._settings(
            tavily_api_key="tavily-key",
            brave_api_key="brave-key",
            serper_api_key="serper-key",
        )
        providers = search_module._build_providers(settings)
        names = {p.name for p in providers}
        self.assertEqual(names, {"tavily", "brave", "serper"})

    def test_normalize_serper_results_skips_missing_url(self) -> None:
        payload = {"organic": [{"title": "No link", "snippet": "Missing URL"}]}
        hits = search_module._normalize_serper_results(payload, "test query")
        self.assertEqual(len(hits), 0)

    def test_normalize_serper_results_maps_fields(self) -> None:
        payload = {
            "organic": [
                {
                    "title": "Serper result",
                    "link": "https://example.com/result",
                    "snippet": "A useful snippet.",
                }
            ]
        }
        hits = search_module._normalize_serper_results(payload, "test query")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0].title, "Serper result")
        self.assertEqual(hits[0].url, "https://example.com/result")
        self.assertEqual(hits[0].snippet, "A useful snippet.")
        self.assertEqual(hits[0].providers, ["serper"])
        self.assertEqual(hits[0].provider_metadata["serper"]["query"], "test query")
        self.assertEqual(hits[0].provider_metadata["serper"]["rank"], 1)
        self.assertIsNone(hits[0].raw_content)

    def test_merge_search_hits_combines_serper_with_other_providers(self) -> None:
        from app.services.research_worker import _merge_search_hits

        hits = [
            SearchHit(
                title="Shared result",
                url="https://example.com/shared",
                snippet="From Tavily",
                providers=["tavily"],
                provider_metadata={"tavily": {"rank": 1}},
            ),
            SearchHit(
                title="Shared result",
                url="https://example.com/shared",
                snippet="From Serper",
                providers=["serper"],
                provider_metadata={"serper": {"rank": 2}},
            ),
        ]
        merged = _merge_search_hits(hits)
        self.assertEqual(len(merged), 1)
        self.assertEqual(sorted(merged[0].providers), ["serper", "tavily"])
        self.assertIn("tavily", merged[0].provider_metadata)
        self.assertIn("serper", merged[0].provider_metadata)


if __name__ == "__main__":
    unittest.main()
