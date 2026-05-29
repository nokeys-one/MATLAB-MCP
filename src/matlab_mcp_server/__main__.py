import sys
import argparse
import logging
from .config import Settings


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="MATLAB MCP Server")
    parser.add_argument("--transport", choices=["stdio", "http"], default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--bind", default=None)
    parser.add_argument("--token", default=None)
    parser.add_argument("--client-vision", choices=["true", "false"], default=None)
    parser.add_argument("--context-limit", type=int, default=None)
    args = parser.parse_args()

    env_overrides = {}
    if args.transport is not None:
        env_overrides["transport"] = args.transport
    if args.port is not None:
        env_overrides["http_port"] = args.port
    if args.bind is not None:
        env_overrides["http_bind"] = args.bind
    if args.token is not None:
        env_overrides["http_token"] = args.token
    if args.client_vision is not None:
        env_overrides["client_vision"] = args.client_vision == "true"
    if args.context_limit is not None:
        env_overrides["context_limit"] = args.context_limit

    settings = Settings(**env_overrides)

    if settings.transport == "stdio":
        from .transport.stdio import run_stdio
        run_stdio(settings)
    else:
        from .transport.http import run_http
        run_http(settings)


if __name__ == "__main__":
    main()
