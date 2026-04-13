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


if __name__ == "__main__":
    unittest.main()
