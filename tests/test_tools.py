from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from support import CLIENT_COMMAND_ID, COMMAND_ID, NEXT_ROUND_ID, ROUND_ID, SESSION_ID

from civarium_mcp.instructions import CIVARIUM_INSTRUCTIONS
from civarium_mcp.resources import (
    OVERVIEW_RESOURCE_URI,
    RULE_CATALOG_MIME_TYPE,
    RULE_CATALOG_RESOURCE_URI,
    RULE_COMMAND_SPEC_RESOURCE_URI_TEMPLATE,
    RULE_COMMAND_TYPES_RESOURCE_URI,
    RULE_ENTITY_SPEC_RESOURCE_URI_TEMPLATE,
    RULE_ENTITY_TYPES_RESOURCE_URI,
    RULE_EVENT_SPEC_RESOURCE_URI_TEMPLATE,
    RULE_EVENT_TYPES_RESOURCE_URI,
    TOOLS_RESOURCE_URI,
    list_civarium_docs,
    load_civarium_doc,
)
from civarium_mcp.schemas import (
    AcceptedCommandListOutput,
    AgentRoundOutput,
    CommandReceivedOutput,
    CommandTypeListOutput,
    CommandTypeSpecOutput,
    EntityTypeListOutput,
    EntityTypeSpecOutput,
    EventTypeListOutput,
    EventTypeSpecOutput,
    VisibleStateOutput,
)
from civarium_mcp.server import create_server

EXPECTED_TOOLS = {
    "get_civarium_context",
    "list_civarium_docs",
    "read_civarium_doc",
    "get_civarium_rule_catalog",
    "list_civarium_command_types",
    "get_civarium_command_spec",
    "list_civarium_entity_types",
    "get_civarium_entity_spec",
    "list_civarium_event_types",
    "get_civarium_event_spec",
    "get_active_round",
    "get_visible_state",
    "submit_command",
    "list_queued_submitted_commands",
    "wait_next_round",
}
EXPECTED_DOC_IDS = {doc.doc_id for doc in list_civarium_docs()}
EXPECTED_DOC_RESOURCE_NAMES = {doc.name for doc in list_civarium_docs()}
EXPECTED_DOC_ID_SCHEMA_ENUM = [doc.doc_id for doc in list_civarium_docs()]
EXPECTED_RULE_RESOURCE_NAMES = {
    "civarium_rule_catalog",
    "civarium_command_types",
    "civarium_entity_types",
    "civarium_event_types",
}
EXPECTED_RULE_RESOURCE_TEMPLATE_NAMES = {
    "civarium_command_spec",
    "civarium_entity_spec",
    "civarium_event_spec",
}


class FakeGateway:
    def __init__(self, rounds: list[UUID] | None = None) -> None:
        self.rounds = rounds or [ROUND_ID]
        self.submitted_payload: dict | None = None

    async def get_active_round(self) -> AgentRoundOutput:
        round_id = self.rounds.pop(0) if len(self.rounds) > 1 else self.rounds[0]
        return AgentRoundOutput(session_id=SESSION_ID, round_id=round_id, round_idx=7)

    async def get_visible_state(self) -> VisibleStateOutput:
        return VisibleStateOutput(round_id=ROUND_ID, entities={})

    async def list_command_types(self) -> CommandTypeListOutput:
        return CommandTypeListOutput(command_types=["construction_start"])

    async def get_command_spec(self, command_type: str) -> CommandTypeSpecOutput:
        return CommandTypeSpecOutput(
            command_type=command_type,
            description="Payload for starting construction.",
            payload_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "rounds_to_complete": {"type": "integer"},
                },
                "required": ["title", "rounds_to_complete"],
            },
            events=["construction_started"],
            validators=[
                {
                    "name": "check_construction_start",
                    "description": "Validate construction start.",
                }
            ],
        )

    async def list_entity_types(self) -> EntityTypeListOutput:
        return EntityTypeListOutput(entity_types=["construction", "structure"])

    async def get_entity_spec(self, entity_type: str) -> EntityTypeSpecOutput:
        return EntityTypeSpecOutput(
            entity_type=entity_type,
            description=f"{entity_type} records.",
            entity_schema={
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "title": {"type": "string"},
                },
            },
        )

    async def list_event_types(self) -> EventTypeListOutput:
        return EventTypeListOutput(
            event_types=[
                "construction_completed",
                "construction_progress",
                "construction_started",
                "structure_created",
            ],
        )

    async def get_event_spec(self, event_type: str) -> EventTypeSpecOutput:
        return EventTypeSpecOutput(
            event_type=event_type,
            description=f"{event_type} payload.",
            payload_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                },
            },
            validators=[
                {
                    "name": f"check_{event_type}",
                    "description": f"Validate {event_type}.",
                }
            ],
            modificator={
                "name": f"on_{event_type}",
                "description": f"Project {event_type}.",
            },
        )

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

    assert "rules catalog" in tools_by_name["get_civarium_rule_catalog"].description
    assert "payload schema" in tools_by_name["list_civarium_command_types"].description
    assert "payload JSON Schema" in tools_by_name["get_civarium_command_spec"].description
    assert "entity library keys" in tools_by_name["list_civarium_entity_types"].description
    assert "records in that entity library" in tools_by_name["get_civarium_entity_spec"].description
    assert "cannot submit them directly" in tools_by_name["list_civarium_event_types"].description
    assert "projection modificator" in tools_by_name["get_civarium_event_spec"].description

    assert "open for the agent's decisions" in tools_by_name["get_active_round"].description
    assert "observable slice of the world" in tools_by_name["get_visible_state"].description
    assert "get_civarium_entity_spec" in tools_by_name["get_visible_state"].description
    assert "command intent" in tools_by_name["submit_command"].description
    assert "not an immediate mutation" in tools_by_name["submit_command"].description
    assert "get_civarium_command_spec" in tools_by_name["submit_command"].description
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
    assert "discover currently registered values" in submit_properties[
        "command_type"
    ]["description"]
    assert "intended game action" in submit_properties["payload"]["description"]
    assert "inspect get_civarium_command_spec" in submit_properties["payload"]["description"]

    command_spec_properties = tools_by_name["get_civarium_command_spec"].inputSchema[
        "properties"
    ]
    assert "discover available values" in command_spec_properties["command_type"]["description"]
    entity_spec_properties = tools_by_name["get_civarium_entity_spec"].inputSchema[
        "properties"
    ]
    assert "discover available values" in entity_spec_properties["entity_type"]["description"]
    event_spec_properties = tools_by_name["get_civarium_event_spec"].inputSchema["properties"]
    assert "discover available values" in event_spec_properties["event_type"]["description"]

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
    assert {resource.name for resource in resources} == (
        EXPECTED_DOC_RESOURCE_NAMES | EXPECTED_RULE_RESOURCE_NAMES
    )
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

    rule_catalog_resource = resources_by_name["civarium_rule_catalog"]
    assert str(rule_catalog_resource.uri) == RULE_CATALOG_RESOURCE_URI
    assert rule_catalog_resource.mimeType == RULE_CATALOG_MIME_TYPE
    assert rule_catalog_resource.description is not None
    assert "backend rules catalog" in rule_catalog_resource.description

    resource_templates = await server.list_resource_templates()
    assert {template.name for template in resource_templates} == (
        EXPECTED_RULE_RESOURCE_TEMPLATE_NAMES
    )
    templates_by_name = {template.name: template for template in resource_templates}
    assert (
        templates_by_name["civarium_command_spec"].uriTemplate
        == RULE_COMMAND_SPEC_RESOURCE_URI_TEMPLATE
    )
    assert (
        templates_by_name["civarium_entity_spec"].uriTemplate
        == RULE_ENTITY_SPEC_RESOURCE_URI_TEMPLATE
    )
    assert (
        templates_by_name["civarium_event_spec"].uriTemplate
        == RULE_EVENT_SPEC_RESOURCE_URI_TEMPLATE
    )
    assert all(template.mimeType == RULE_CATALOG_MIME_TYPE for template in resource_templates)


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


def test_static_docs_route_runtime_rule_specs_to_rules_catalog() -> None:
    forbidden_static_spec_fragments = (
        "construction_start",
        "`construction`",
        "`structure`",
        "rounds_to_complete",
        "owner-based",
        "Payload fields",
        "Visible fields",
    )

    for doc in list_civarium_docs():
        content = load_civarium_doc(doc.doc_id)

        assert "civarium://rules/" in content or "get_civarium_rule_catalog" in content
        for fragment in forbidden_static_spec_fragments:
            assert fragment not in content


async def test_rule_catalog_available_through_tools(adapter_config) -> None:
    server = create_server(adapter_config, gateway=FakeGateway())

    catalog_result = await server.call_tool("get_civarium_rule_catalog", {})
    catalog_output = structured_content(catalog_result)

    assert catalog_output["resources"]["catalog_uri"] == RULE_CATALOG_RESOURCE_URI
    assert catalog_output["resources"]["command_types_uri"] == RULE_COMMAND_TYPES_RESOURCE_URI
    assert (
        catalog_output["resources"]["command_spec_uri_template"]
        == RULE_COMMAND_SPEC_RESOURCE_URI_TEMPLATE
    )
    assert catalog_output["resources"]["entity_types_uri"] == RULE_ENTITY_TYPES_RESOURCE_URI
    assert (
        catalog_output["resources"]["entity_spec_uri_template"]
        == RULE_ENTITY_SPEC_RESOURCE_URI_TEMPLATE
    )
    assert catalog_output["resources"]["event_types_uri"] == RULE_EVENT_TYPES_RESOURCE_URI
    assert (
        catalog_output["resources"]["event_spec_uri_template"]
        == RULE_EVENT_SPEC_RESOURCE_URI_TEMPLATE
    )
    assert catalog_output["command_types"] == ["construction_start"]
    assert catalog_output["entity_types"] == ["construction", "structure"]
    assert "construction_started" in catalog_output["event_types"]

    command_types_result = await server.call_tool("list_civarium_command_types", {})
    command_types_output = structured_content(command_types_result)
    assert command_types_output == {"command_types": ["construction_start"]}

    command_spec_result = await server.call_tool(
        "get_civarium_command_spec",
        {"command_type": "construction_start"},
    )
    command_spec_output = structured_content(command_spec_result)
    assert command_spec_output["command_type"] == "construction_start"
    assert command_spec_output["events"] == ["construction_started"]
    assert command_spec_output["validators"][0]["name"] == "check_construction_start"
    assert "rounds_to_complete" in command_spec_output["payload_schema"]["properties"]

    entity_types_result = await server.call_tool("list_civarium_entity_types", {})
    entity_types_output = structured_content(entity_types_result)
    assert entity_types_output == {"entity_types": ["construction", "structure"]}

    entity_spec_result = await server.call_tool(
        "get_civarium_entity_spec",
        {"entity_type": "structure"},
    )
    entity_spec_output = structured_content(entity_spec_result)
    assert entity_spec_output["entity_type"] == "structure"
    assert "owner" in entity_spec_output["entity_schema"]["properties"]

    event_types_result = await server.call_tool("list_civarium_event_types", {})
    event_types_output = structured_content(event_types_result)
    assert "construction_completed" in event_types_output["event_types"]

    event_spec_result = await server.call_tool(
        "get_civarium_event_spec",
        {"event_type": "construction_started"},
    )
    event_spec_output = structured_content(event_spec_result)
    assert event_spec_output["event_type"] == "construction_started"
    assert event_spec_output["modificator"]["name"] == "on_construction_started"


async def test_rule_catalog_available_as_resources(adapter_config) -> None:
    server = create_server(adapter_config, gateway=FakeGateway())

    catalog_contents = await server.read_resource(RULE_CATALOG_RESOURCE_URI)
    assert len(catalog_contents) == 1
    assert catalog_contents[0].mime_type == RULE_CATALOG_MIME_TYPE
    catalog = json.loads(catalog_contents[0].content)
    assert catalog["command_types"] == ["construction_start"]
    assert catalog["entity_types"] == ["construction", "structure"]
    assert catalog["resources"]["event_types_uri"] == RULE_EVENT_TYPES_RESOURCE_URI

    command_list_contents = await server.read_resource(RULE_COMMAND_TYPES_RESOURCE_URI)
    assert len(command_list_contents) == 1
    assert command_list_contents[0].mime_type == RULE_CATALOG_MIME_TYPE
    assert json.loads(command_list_contents[0].content) == {
        "command_types": ["construction_start"]
    }

    command_spec_contents = await server.read_resource(
        "civarium://rules/commands/construction_start",
    )
    assert len(command_spec_contents) == 1
    assert command_spec_contents[0].mime_type == RULE_CATALOG_MIME_TYPE
    command_spec = json.loads(command_spec_contents[0].content)
    assert command_spec["command_type"] == "construction_start"
    assert command_spec["events"] == ["construction_started"]

    entity_spec_contents = await server.read_resource("civarium://rules/entities/structure")
    assert len(entity_spec_contents) == 1
    assert entity_spec_contents[0].mime_type == RULE_CATALOG_MIME_TYPE
    assert json.loads(entity_spec_contents[0].content)["entity_type"] == "structure"

    event_spec_contents = await server.read_resource(
        "civarium://rules/events/construction_started",
    )
    assert len(event_spec_contents) == 1
    assert event_spec_contents[0].mime_type == RULE_CATALOG_MIME_TYPE
    assert json.loads(event_spec_contents[0].content)["modificator"]["name"] == (
        "on_construction_started"
    )


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
