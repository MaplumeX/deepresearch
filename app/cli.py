from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

import uvicorn

from app.config import load_env_file, read_bool_env

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True, slots=True)
class ServerOptions:
    host: str
    port: int
    reload: bool


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Start the deepresearch backend API.")
    parser.add_argument("--host", help="Bind host. Defaults to APP_HOST or 127.0.0.1.")
    parser.add_argument("--port", type=int, help="Bind port. Defaults to APP_PORT or 8000.")
    parser.add_argument(
        "--reload",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Enable or disable auto-reload. Defaults to APP_RELOAD or enabled.",
    )
    return parser


def _resolve_server_options(args: argparse.Namespace) -> ServerOptions:
    host = args.host or os.getenv("APP_HOST", "127.0.0.1")
    port = args.port if args.port is not None else int(os.getenv("APP_PORT", "8000"))
    reload_enabled = args.reload if args.reload is not None else read_bool_env("APP_RELOAD", True)
    return ServerOptions(host=host, port=port, reload=reload_enabled)


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)

    load_env_file(PROJECT_ROOT / ".env")
    options = _resolve_server_options(args)

    uvicorn_kwargs: dict[str, object] = {
        "host": options.host,
        "port": options.port,
        "reload": options.reload,
    }
    if options.reload:
        uvicorn_kwargs["reload_dirs"] = [str(PROJECT_ROOT / "app")]

    uvicorn.run("app.main:app", **uvicorn_kwargs)


if __name__ == "__main__":
    main()
