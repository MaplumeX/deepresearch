from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from app.config import get_settings


class ConfigTest(unittest.TestCase):
    def tearDown(self) -> None:
        get_settings.cache_clear()

    def test_prefers_generic_llm_env_names(self) -> None:
        with patch.dict(
            os.environ,
            {
                "LLM_API_KEY": "generic-key",
                "LLM_BASE_URL": "https://compatible.example/v1",
                "OPENAI_API_KEY": "legacy-key",
                "OPENAI_BASE_URL": "https://legacy.example/v1",
            },
            clear=False,
        ):
            get_settings.cache_clear()
            settings = get_settings()

        self.assertEqual(settings.llm_api_key, "generic-key")
        self.assertEqual(settings.llm_base_url, "https://compatible.example/v1")

    def test_falls_back_to_openai_aliases(self) -> None:
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "legacy-key",
                "OPENAI_BASE_URL": "https://legacy.example/v1",
            },
            clear=True,
        ):
            get_settings.cache_clear()
            settings = get_settings()

        self.assertEqual(settings.llm_api_key, "legacy-key")
        self.assertEqual(settings.llm_base_url, "https://legacy.example/v1")

    def test_uses_default_runs_db_path(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            get_settings.cache_clear()
            settings = get_settings()

        self.assertEqual(settings.runs_db_path, "research_runs.db")
        self.assertIsNone(settings.brave_api_key)
        self.assertIsNone(settings.serper_api_key)
        self.assertEqual(settings.synthesis_soft_char_limit, 90000)
        self.assertEqual(settings.synthesis_hard_char_limit, 110000)
        self.assertEqual(settings.synthesis_max_findings_per_call, 24)
        self.assertEqual(settings.synthesis_max_sources_per_call, 12)

    def test_loads_serper_api_key(self) -> None:
        with patch.dict(os.environ, {"SERPER_API_KEY": "serper-test-key"}, clear=True):
            get_settings.cache_clear()
            settings = get_settings()

        self.assertEqual(settings.serper_api_key, "serper-test-key")

    def test_enables_remote_fallbacks_when_keys_exist(self) -> None:
        with patch.dict(
            os.environ,
            {
                "JINA_API_KEY": "jina-test-key",
                "FIRECRAWL_API_KEY": "firecrawl-test-key",
            },
            clear=True,
        ):
            get_settings.cache_clear()
            settings = get_settings()

        self.assertEqual(settings.jina_api_key, "jina-test-key")
        self.assertEqual(settings.firecrawl_api_key, "firecrawl-test-key")
        self.assertTrue(settings.enable_jina_reader_fallback)
        self.assertTrue(settings.enable_firecrawl_fallback)

    def test_can_enable_jina_reader_without_api_key(self) -> None:
        with patch.dict(os.environ, {"ENABLE_JINA_READER_FALLBACK": "true"}, clear=True):
            get_settings.cache_clear()
            settings = get_settings()

        self.assertIsNone(settings.jina_api_key)
        self.assertTrue(settings.enable_jina_reader_fallback)
        self.assertFalse(settings.enable_firecrawl_fallback)


if __name__ == "__main__":
    unittest.main()
