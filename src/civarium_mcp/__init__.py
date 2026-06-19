"""Civarium MCP adapter package."""

from civarium_mcp.version import __version__

__all__ = ["__version__", "main"]


def main() -> int:
    """Console-script compatibility wrapper."""
    from civarium_mcp.__main__ import main as cli_main

    return cli_main()
