from __future__ import annotations

import argparse
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.cli import PROJECT_ROOT, _resolve_server_options, main
from app.config import load_env_file


class CliTest(unittest.TestCase):
    def test_load_env_file_returns_false_for_missing_file(self) -> None:
        missing_path = Path(tempfile.gettempdir()) / "deepresearch-missing.env"
        self.assertFalse(load_env_file(missing_path))

    def test_load_env_file_sets_only_missing_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            env_path.write_text(
                "# comment\n"
                "export APP_HOST=0.0.0.0\n"
                "APP_PORT=9000\n"
                "APP_NAME='quoted-name'\n",
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"APP_PORT": "7000"}, clear=True):
                self.assertTrue(load_env_file(env_path))
                self.assertEqual(os.environ["APP_HOST"], "0.0.0.0")
                self.assertEqual(os.environ["APP_PORT"], "7000")
                self.assertEqual(os.environ["APP_NAME"], "quoted-name")

    def test_resolve_server_options_uses_env_defaults(self) -> None:
        args = argparse.Namespace(host=None, port=None, reload=None)
        with patch.dict(
            os.environ,
            {"APP_HOST": "0.0.0.0", "APP_PORT": "9000", "APP_RELOAD": "false"},
            clear=True,
        ):
            options = _resolve_server_options(args)

        self.assertEqual(options.host, "0.0.0.0")
        self.assertEqual(options.port, 9000)
        self.assertFalse(options.reload)

    def test_main_loads_repo_env_and_starts_uvicorn(self) -> None:
        with (
            patch("app.cli.load_env_file") as mock_load_env_file,
            patch("app.cli.uvicorn.run") as mock_uvicorn_run,
        ):
            main(["--host", "0.0.0.0", "--port", "9001", "--no-reload"])

        mock_load_env_file.assert_called_once_with(PROJECT_ROOT / ".env")
        mock_uvicorn_run.assert_called_once_with(
            "app.main:app",
            host="0.0.0.0",
            port=9001,
            reload=False,
        )

    def test_main_watches_app_dir_when_reload_enabled(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            patch("app.cli.load_env_file"),
            patch("app.cli.uvicorn.run") as mock_uvicorn_run,
        ):
            main([])

        self.assertEqual(mock_uvicorn_run.call_args.args[0], "app.main:app")
        self.assertEqual(mock_uvicorn_run.call_args.kwargs["host"], "127.0.0.1")
        self.assertEqual(mock_uvicorn_run.call_args.kwargs["port"], 8000)
        self.assertTrue(mock_uvicorn_run.call_args.kwargs["reload"])
        self.assertEqual(
            mock_uvicorn_run.call_args.kwargs["reload_dirs"],
            [str(PROJECT_ROOT / "app")],
        )


if __name__ == "__main__":
    unittest.main()
