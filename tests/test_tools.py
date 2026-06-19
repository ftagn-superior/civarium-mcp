from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from support import CLIENT_COMMAND_ID, COMMAND_ID, NEXT_ROUND_ID, ROUND_ID, SESSION_ID

from civarium_mcp.schemas import (
    AcceptedCommandListOutput,
    AgentRoundOutput,
    CommandReceivedOutput,
    VisibleStateOutput,
)
from civarium_mcp.server import create_server

EXPECTED_TOOLS = {
    "get_active_round",
    "get_visible_state",
    "submit_command",
    "list_my_commands",
    "wait_next_round",
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

    async def list_my_commands(self, round_id: UUID) -> AcceptedCommandListOutput:
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

    assert {tool.name for tool in tools} == EXPECTED_TOOLS
    tools_by_name = {tool.name: tool for tool in tools}
    for tool in tools:
        schema = json.dumps(tool.inputSchema)
        assert "agent_id" not in schema
        assert "session_id" not in schema

    assert tools_by_name["submit_command"].annotations is not None
    assert tools_by_name["submit_command"].annotations.readOnlyHint is False
    assert tools_by_name["submit_command"].annotations.destructiveHint is False
    assert tools_by_name["submit_command"].annotations.idempotentHint is False

    for tool_name in EXPECTED_TOOLS - {"submit_command"}:
        annotations = tools_by_name[tool_name].annotations
        assert annotations is not None
        assert annotations.readOnlyHint is True
        assert annotations.destructiveHint is False
        assert annotations.idempotentHint is True
        assert annotations.openWorldHint is False

    assert await server.list_prompts() == []
    assert await server.list_resources() == []


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
