"""Command-line entrypoint for the Civarium MCP adapter."""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Sequence

from pydantic import ValidationError

from civarium_mcp.config import AdapterConfig, format_config_error
from civarium_mcp.gateway import CivariumApiError, HttpCivariumGateway
from civarium_mcp.server import run_stdio
from civarium_mcp.version import __version__


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI."""
    parser = argparse.ArgumentParser(
        prog="civarium-mcp",
        description="Hermes-compatible local MCP adapter for Civarium.",
    )
    parser.add_argument("--version", action="store_true", help="Print adapter version and exit.")
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="Validate adapter environment without starting MCP stdio.",
    )
    parser.add_argument(
        "--ping",
        action="store_true",
        help="With --check-config, call GET /api/v1/agent/round to verify credentials.",
    )

    args = parser.parse_args(argv)

    if args.version:
        print(f"civarium-mcp {__version__}")
        return 0

    if args.ping and not args.check_config:
        parser.error("--ping can only be used with --check-config")

    config = _load_config()
    if config is None:
        return 2

    if args.check_config:
        if args.ping:
            return asyncio.run(_ping(config))
        print("civarium-mcp configuration OK", file=sys.stderr)
        return 0

    try:
        asyncio.run(run_stdio(config))
    except KeyboardInterrupt:
        return 130
    return 0


def _load_config() -> AdapterConfig | None:
    try:
        return AdapterConfig()
    except ValidationError as exc:
        print(
            f"civarium-mcp configuration error: {format_config_error(exc)}",
            file=sys.stderr,
        )
        return None


async def _ping(config: AdapterConfig) -> int:
    gateway = HttpCivariumGateway(config)
    try:
        active_round = await gateway.get_active_round()
    except CivariumApiError as exc:
        print(f"civarium-mcp ping failed: {exc}", file=sys.stderr)
        return 1

    print(
        "civarium-mcp configuration OK; "
        f"Civarium API reachable (round_id={active_round.round_id}, "
        f"round_idx={active_round.round_idx})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
