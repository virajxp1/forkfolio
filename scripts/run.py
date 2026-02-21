#!/usr/bin/env python3

import argparse
import os
import sys

import uvicorn

# Add project root to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.insert(0, project_root)

DEFAULT_PORT = 8000


def _env_truthy(name: str) -> bool:
    value = os.getenv(name, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _resolve_port(cli_port: int | None) -> int:
    if cli_port is not None:
        return cli_port

    env_port = os.getenv("PORT", "").strip()
    if env_port:
        try:
            port = int(env_port)
        except ValueError as exc:
            raise SystemExit(
                f"Invalid PORT value '{env_port}'. PORT must be an integer."
            ) from exc

        if not (1 <= port <= 65535):
            raise SystemExit(
                f"Invalid PORT value '{env_port}'. PORT must be between 1 and 65535."
            )

        return port

    return DEFAULT_PORT


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the ForkFolio API server with production-safe defaults."
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument(
        "--reload",
        dest="reload",
        action="store_true",
        default=_env_truthy("UVICORN_RELOAD"),
        help="Enable auto-reload (development only).",
    )
    parser.add_argument(
        "--no-reload",
        dest="reload",
        action="store_false",
        help="Disable auto-reload (default).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    # Change to project root directory
    os.chdir(project_root)
    args = _parse_args()
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=_resolve_port(args.port),
        reload=args.reload,
    )
