from __future__ import annotations

import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

EXPECTED_TOOLS = {
    "get_civarium_context",
    "list_civarium_docs",
    "read_civarium_doc",
    "get_active_round",
    "get_visible_state",
    "submit_command",
    "list_queued_submitted_commands",
    "wait_next_round",
}


def test_hermes_example_exposes_only_expected_tools() -> None:
    text = Path("examples/hermes.config.yaml").read_text()

    assert 'command: "uvx"' in text
    assert 'args: ["civarium-mcp==0.1.5"]' in text
    assert "supports_parallel_tool_calls: false" in text
    assert "prompts: false" in text
    assert "resources: true" in text
    for tool_name in EXPECTED_TOOLS:
        assert f"        - {tool_name}" in text


async def test_stdio_server_supports_tool_discovery_without_backend(tmp_path: Path) -> None:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "civarium_mcp"],
        env={
            "CIVARIUM_BASE_URL": "https://api.civarium.example",
            "CIVARIUM_AGENT_API_KEY": "agent-secret",
        },
    )

    errlog_path = tmp_path / "stderr.log"
    with errlog_path.open("w+") as errlog:
        async with stdio_client(server_params, errlog=errlog) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()

    assert {tool.name for tool in tools.tools} == EXPECTED_TOOLS
    assert "agent-secret" not in errlog_path.read_text()
