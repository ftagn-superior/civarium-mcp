"""Stdio MCP server factory for Civarium."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from civarium_mcp.config import AdapterConfig
from civarium_mcp.gateway import HttpCivariumGateway
from civarium_mcp.instructions import CIVARIUM_INSTRUCTIONS
from civarium_mcp.tools import register_tools


def create_server(
    config: AdapterConfig | None = None,
    *,
    gateway: HttpCivariumGateway | None = None,
) -> FastMCP:
    """Create a Civarium MCP server with only player-facing tools registered."""
    resolved_config = config or AdapterConfig()
    resolved_gateway = gateway or HttpCivariumGateway(resolved_config)
    server = FastMCP(
        name="civarium",
        instructions=CIVARIUM_INSTRUCTIONS,
        log_level="INFO",
    )
    register_tools(server, gateway=resolved_gateway, config=resolved_config)
    return server


async def run_stdio(config: AdapterConfig | None = None) -> None:
    """Run the Civarium MCP server over stdio."""
    server = create_server(config)
    await server.run_stdio_async()
