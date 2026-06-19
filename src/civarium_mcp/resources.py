"""Static MCP resources for Civarium reference context."""

from __future__ import annotations

from importlib.resources import files

from mcp.server.fastmcp import FastMCP

OVERVIEW_RESOURCE_URI = "civarium://docs/overview"
OVERVIEW_RESOURCE_NAME = "civarium_overview"
OVERVIEW_RESOURCE_TITLE = "Civarium Overview"
OVERVIEW_MIME_TYPE = "text/markdown"
TOOLS_RESOURCE_URI = "civarium://docs/tools"
TOOLS_RESOURCE_NAME = "civarium_tools"
TOOLS_RESOURCE_TITLE = "Civarium Agent Tools"
TOOLS_MIME_TYPE = "text/markdown"


def load_civarium_overview() -> str:
    """Return the canonical static overview for Civarium agents."""
    return (
        files("civarium_mcp.docs")
        .joinpath("civarium-overview.md")
        .read_text(encoding="utf-8")
    )


def load_civarium_tools() -> str:
    """Return the canonical static tool specification for Civarium agents."""
    return (
        files("civarium_mcp.docs")
        .joinpath("civarium-tools.md")
        .read_text(encoding="utf-8")
    )


def register_resources(server: FastMCP) -> None:
    """Register static Civarium reference documents as MCP resources."""

    @server.resource(
        OVERVIEW_RESOURCE_URI,
        name=OVERVIEW_RESOURCE_NAME,
        title=OVERVIEW_RESOURCE_TITLE,
        description=(
            "Canonical high-level Markdown overview explaining what Civarium is, "
            "how agents relate to the game world, and how to interpret rounds, "
            "visible state, and command intents."
        ),
        mime_type=OVERVIEW_MIME_TYPE,
    )
    def get_civarium_overview() -> str:
        return load_civarium_overview()

    @server.resource(
        TOOLS_RESOURCE_URI,
        name=TOOLS_RESOURCE_NAME,
        title=TOOLS_RESOURCE_TITLE,
        description=(
            "Markdown specification of the MCP tools available to a Civarium agent, "
            "including their game-world meaning, key inputs, outputs, and suggested "
            "decision loop."
        ),
        mime_type=TOOLS_MIME_TYPE,
    )
    def get_civarium_tools() -> str:
        return load_civarium_tools()
