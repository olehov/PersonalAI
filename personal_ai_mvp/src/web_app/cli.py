"""CLI bootstrap for the PersonalAI web UI server."""

from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer
from pathlib import Path

from infrastructure.config.settings import get_settings
from web_app.app import PersonalAIWebApp
from web_app.http import make_handler


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the web UI."""
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run the PersonalAI local web UI.")
    parser.add_argument("--vault", type=Path, required=True, help="Path to the Obsidian vault root.")
    parser.add_argument("--host", default=settings.ui_host, help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=settings.ui_port, help="Port to bind.")
    parser.add_argument(
        "--ollama-base-url",
        default=settings.ollama_base_url,
        help="Base URL for the local Ollama server.",
    )
    parser.add_argument(
        "--ollama-timeout-seconds",
        type=int,
        help="Optional timeout for Ollama HTTP calls in seconds. Overrides OLLAMA_TIMEOUT_SECONDS.",
    )
    parser.add_argument(
        "--frontend-dist-dir",
        type=Path,
        default=settings.frontend_dist_dir,
        help="Path to the built frontend dist directory served for the JS UI.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the local web UI server."""
    args = build_parser().parse_args(argv)
    app = PersonalAIWebApp(
        vault_root=args.vault,
        ollama_base_url=args.ollama_base_url,
        ollama_timeout_seconds=args.ollama_timeout_seconds,
        frontend_dist_dir=args.frontend_dist_dir,
    )
    server = ThreadingHTTPServer((args.host, args.port), make_handler(app))
    print(f"PersonalAI UI running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
