from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from support import CLIENT_COMMAND_ID, COMMAND_ID, NEXT_ROUND_ID, ROUND_ID, SESSION_ID

from civarium_mcp.instructions import CIVARIUM_INSTRUCTIONS
from civarium_mcp.resources import (
    OVERVIEW_RESOURCE_URI,
    TOOLS_RESOURCE_URI,
    list_civarium_docs,
)
from civarium_mcp.schemas import (
    AcceptedCommandListOutput,
    AgentRoundOutput,
    CommandReceivedOutput,
    VisibleStateOutput,
)
from civarium_mcp.server import create_server

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
EXPECTED_DOC_IDS = {doc.doc_id for doc in list_civarium_docs()}
EXPECTED_DOC_RESOURCE_NAMES = {doc.name for doc in list_civarium_docs()}
EXPECTED_DOC_ID_SCHEMA_ENUM = [doc.doc_id for doc in list_civarium_docs()]


class FakeGateway:
    def __init__(self, rounds: list[UUID] | None = None) -> None:
        self.rounds = rounds or [ROUND_ID]
        self.submitted_payload: dict | None = None

    async def get_active_round(self) -> AgentRoundOutput:
        round_id = self.rounds.pop(0) if len(self.rounds) > 1 else self.rounds[0]
        return AgentRoundOutput(session_id=SESSION_ID, round_id=round_id, round_idx=7)

    async def get_visible_state(self) -> VisibleStateOutput:
        return VisibleStateOutput(round_id=ROUND_ID, entities={})

    async def submit_command(
        self,
        *,
        round_id: UUID,
        client_command_id: UUID,
        command_type: str,
        payload: dict,
    ) -> CommandReceivedOutput:
        self.submitted_payload = payload
        return CommandReceivedOutput(
            command_id=COMMAND_ID,
            round_id=round_id,
            client_command_id=client_command_id,
            is_valid=False,
            checks={"rule": "failed"},
        )

    async def list_queued_submitted_commands(
        self,
        round_id: UUID,
    ) -> AcceptedCommandListOutput:
        return AcceptedCommandListOutput(
            round_id=round_id,
            commands=[
                {
                    "command_id": COMMAND_ID,
                    "client_command_id": CLIENT_COMMAND_ID,
                    "command_type": "construction_start",
                    "payload": {"title": "Granary"},
                    "created_at": datetime.now(tz=UTC),
                }
            ],
        )


def structured_content(result) -> dict:
    if isinstance(result, tuple):
        return result[1]
    if isinstance(result, dict):
        return result
    raise TypeError(f"unexpected tool result: {result!r}")


async def test_server_exposes_only_expected_tools(adapter_config) -> None:
    server = create_server(adapter_config, gateway=FakeGateway())

    tools = await server.list_tools()

    assert server.instructions == CIVARIUM_INSTRUCTIONS
    assert {tool.name for tool in tools} == EXPECTED_TOOLS
    tools_by_name = {tool.name: tool for tool in tools}
    for tool in tools:
        schema = json.dumps(tool.inputSchema)
        assert "agent_id" not in schema
        assert "session_id" not in schema

    assert "static Civarium overview" in tools_by_name["get_civarium_context"].description
    assert "MCP clients that expose tools" in tools_by_name["get_civarium_context"].description
    assert "looking for Civarium documentation" in tools_by_name["list_civarium_docs"].description
    assert "Read one static Civarium Markdown document" in tools_by_name[
        "read_civarium_doc"
    ].description
    assert tools_by_name["submit_command"].annotations is not None
    assert tools_by_name["submit_command"].annotations.readOnlyHint is False
    assert tools_by_name["submit_command"].annotations.destructiveHint is False
    assert tools_by_name["submit_command"].annotations.idempotentHint is False

    assert "open for the agent's decisions" in tools_by_name["get_active_round"].description
    assert "observable slice of the world" in tools_by_name["get_visible_state"].description
    assert "`construction` and `structure`" in tools_by_name["get_visible_state"].description
    assert "command intent" in tools_by_name["submit_command"].description
    assert "not an immediate mutation" in tools_by_name["submit_command"].description
    assert "`construction_start`" in tools_by_name["submit_command"].description
    assert "submitted command intents" in tools_by_name[
        "list_queued_submitted_commands"
    ].description
    assert (
        "does not list available command types"
        in tools_by_name["list_queued_submitted_commands"].description
    )
    assert "never advances the Civarium session" in tools_by_name["wait_next_round"].description

    submit_properties = tools_by_name["submit_command"].inputSchema["properties"]
    assert "agent decision" in submit_properties["round_id"]["description"]
    assert "idempotency key" in submit_properties["client_command_id"]["description"]
    assert "backend command handler" in submit_properties["command_type"]["description"]
    assert "current implemented command type" in submit_properties["command_type"]["description"]
    assert "intended game action" in submit_properties["payload"]["description"]
    assert "`title` and `rounds_to_complete`" in submit_properties["payload"]["description"]

    wait_properties = tools_by_name["wait_next_round"].inputSchema["properties"]
    assert "already observed by the agent" in wait_properties["after_round_id"]["description"]
    assert "never used to advance the session" in wait_properties["timeout_seconds"]["description"]

    read_doc_properties = tools_by_name["read_civarium_doc"].inputSchema["properties"]
    assert read_doc_properties["doc_id"]["enum"] == EXPECTED_DOC_ID_SCHEMA_ENUM
    assert "Static Civarium document id" in read_doc_properties["doc_id"]["description"]

    for tool_name in EXPECTED_TOOLS - {"submit_command"}:
        annotations = tools_by_name[tool_name].annotations
        assert annotations is not None
        assert annotations.readOnlyHint is True
        assert annotations.destructiveHint is False
        assert annotations.idempotentHint is True
        assert annotations.openWorldHint is False

    assert await server.list_prompts() == []
    resources = await server.list_resources()
    assert {resource.name for resource in resources} == EXPECTED_DOC_RESOURCE_NAMES
    resources_by_name = {resource.name: resource for resource in resources}
    overview_resource = resources_by_name["civarium_overview"]
    assert str(overview_resource.uri) == OVERVIEW_RESOURCE_URI
    assert overview_resource.mimeType == "text/markdown"
    assert overview_resource.description is not None
    assert "high-level Civarium premise" in overview_resource.description

    tools_resource = resources_by_name["civarium_tools"]
    assert str(tools_resource.uri) == TOOLS_RESOURCE_URI
    assert tools_resource.mimeType == "text/markdown"
    assert tools_resource.description is not None
    assert "available MCP tools" in tools_resource.description


async def test_civarium_context_available_as_tool_and_resource(adapter_config) -> None:
    server = create_server(adapter_config, gateway=FakeGateway())

    tool_result = await server.call_tool("get_civarium_context", {})
    tool_output = structured_content(tool_result)

    assert tool_output["uri"] == OVERVIEW_RESOURCE_URI
    assert tool_output["title"] == "Civarium Overview"
    assert tool_output["mime_type"] == "text/markdown"
    assert "Civarium is an agent-native turn-based strategy sandbox" in tool_output["content"]
    assert "player-facing interface to the Civarium game" in tool_output["content"]

    resource_contents = await server.read_resource(OVERVIEW_RESOURCE_URI)

    assert len(resource_contents) == 1
    assert resource_contents[0].mime_type == "text/markdown"
    assert resource_contents[0].content == tool_output["content"]


async def test_civarium_docs_available_through_tools(adapter_config) -> None:
    server = create_server(adapter_config, gateway=FakeGateway())

    list_result = await server.call_tool("list_civarium_docs", {})
    list_output = structured_content(list_result)

    assert {doc["doc_id"] for doc in list_output["docs"]} == EXPECTED_DOC_IDS
    docs_by_id = {doc["doc_id"]: doc for doc in list_output["docs"]}
    assert docs_by_id["overview"]["uri"] == OVERVIEW_RESOURCE_URI
    assert docs_by_id["tools"]["uri"] == TOOLS_RESOURCE_URI
    assert docs_by_id["world-model"]["uri"] == "civarium://docs/world-model"
    assert docs_by_id["agent-knowledge"]["uri"] == "civarium://docs/agent-knowledge"
    assert docs_by_id["command-lifecycle"]["uri"] == "civarium://docs/command-lifecycle"
    assert docs_by_id["current-mechanics"]["uri"] == "civarium://docs/current-mechanics"
    assert docs_by_id["glossary"]["uri"] == "civarium://docs/glossary"
    assert docs_by_id["overview"]["mime_type"] == "text/markdown"
    assert "Civarium" in docs_by_id["tools"]["title"]
    assert all(doc["description"].startswith("Read this") for doc in list_output["docs"])
    assert "knowledge boundaries" in docs_by_id["agent-knowledge"]["description"]
    assert "queued commands" in docs_by_id["command-lifecycle"]["description"]

    read_result = await server.call_tool("read_civarium_doc", {"doc_id": "tools"})
    read_output = structured_content(read_result)

    assert read_output["doc_id"] == "tools"
    assert read_output["uri"] == TOOLS_RESOURCE_URI
    assert read_output["title"] == "Civarium Agent Tools"
    assert read_output["mime_type"] == "text/markdown"
    assert "# Civarium Agent Tools" in read_output["content"]
    assert "`submit_command`" in read_output["content"]

    glossary_result = await server.call_tool("read_civarium_doc", {"doc_id": "glossary"})
    glossary_output = structured_content(glossary_result)

    assert glossary_output["doc_id"] == "glossary"
    assert glossary_output["uri"] == "civarium://docs/glossary"
    assert "# Civarium Glossary" in glossary_output["content"]
    assert "Command Intent" in glossary_output["content"]


async def test_civarium_tools_spec_available_as_resource(adapter_config) -> None:
    server = create_server(adapter_config, gateway=FakeGateway())

    resource_contents = await server.read_resource(TOOLS_RESOURCE_URI)

    assert len(resource_contents) == 1
    assert resource_contents[0].mime_type == "text/markdown"
    assert "# Civarium Agent Tools" in resource_contents[0].content
    assert "`get_active_round`" in resource_contents[0].content
    assert "`submit_command`" in resource_contents[0].content
    assert "Suggested Decision Loop" in resource_contents[0].content


async def test_static_agent_context_docs_available_as_resources(adapter_config) -> None:
    server = create_server(adapter_config, gateway=FakeGateway())
    expected_headings = {
        "world-model": "# Civarium World Model",
        "agent-knowledge": "# Civarium Agent Knowledge",
        "command-lifecycle": "# Civarium Command Lifecycle",
        "current-mechanics": "# Civarium Current Mechanics",
        "glossary": "# Civarium Glossary",
    }

    for doc in list_civarium_docs():
        if doc.doc_id not in expected_headings:
            continue

        resource_contents = await server.read_resource(doc.uri)

        assert len(resource_contents) == 1
        assert resource_contents[0].mime_type == "text/markdown"
        assert expected_headings[doc.doc_id] in resource_contents[0].content
        assert "## Implemented" in resource_contents[0].content
        assert "## Design Direction" in resource_contents[0].content


async def test_submit_command_returns_structured_invalid_receipt(adapter_config) -> None:
    gateway = FakeGateway()
    server = create_server(adapter_config, gateway=gateway)

    result = await server.call_tool(
        "submit_command",
        {
            "round_id": str(ROUND_ID),
            "client_command_id": str(CLIENT_COMMAND_ID),
            "command_type": "construction_start",
            "payload": {"title": "Granary"},
        },
    )

    output = structured_content(result)
    assert output["is_valid"] is False
    assert output["checks"] == {"rule": "failed"}
    assert gateway.submitted_payload == {"title": "Granary"}


async def test_wait_next_round_returns_changed_when_round_differs(adapter_config) -> None:
    server = create_server(adapter_config, gateway=FakeGateway(rounds=[NEXT_ROUND_ID]))

    result = await server.call_tool(
        "wait_next_round",
        {"after_round_id": str(ROUND_ID), "timeout_seconds": 0.01},
    )

    output = structured_content(result)
    assert output["status"] == "changed"
    assert output["timed_out"] is False
    assert output["round"]["round_id"] == str(NEXT_ROUND_ID)


async def test_wait_next_round_returns_structured_timeout(adapter_config) -> None:
    server = create_server(adapter_config, gateway=FakeGateway(rounds=[ROUND_ID]))

    result = await server.call_tool(
        "wait_next_round",
        {"after_round_id": str(ROUND_ID), "timeout_seconds": 0.005},
    )

    output = structured_content(result)
    assert output["status"] == "timeout"
    assert output["timed_out"] is True
    assert output["round"]["round_id"] == str(ROUND_ID)
