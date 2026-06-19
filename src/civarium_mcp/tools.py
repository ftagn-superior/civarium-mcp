"""MCP tool registrations for Civarium."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any
from uuid import UUID

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from civarium_mcp.config import AdapterConfig
from civarium_mcp.gateway import HttpCivariumGateway
from civarium_mcp.schemas import (
    AcceptedCommandListOutput,
    AgentRoundOutput,
    CommandReceivedOutput,
    VisibleStateOutput,
    WaitNextRoundOutput,
)

RoundIdParam = Annotated[UUID, Field(description="Civarium round UUID.")]
ClientCommandIdParam = Annotated[
    UUID,
    Field(description="Caller-generated UUID that must be unique per submitted command."),
]
CommandTypeParam = Annotated[
    str,
    Field(description="Civarium command type, for example `construction_start`."),
]
CommandPayloadParam = Annotated[
    dict[str, Any],
    Field(
        description=(
            "Opaque command payload. Shape depends on command_type and is validated by "
            "the Civarium backend command registry; see Civarium command documentation."
        ),
    ),
]
TimeoutParam = Annotated[
    float,
    Field(gt=0, description="Requested wait timeout in seconds; capped by adapter config."),
]

READ_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
WRITE_TOOL_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=False,
)


def register_tools(
    server: FastMCP,
    *,
    gateway: HttpCivariumGateway,
    config: AdapterConfig,
) -> None:
    """Register the five player-facing Civarium tools."""
    wait_lock = asyncio.Lock()

    @server.tool(
        description="Return the active Civarium round for the authenticated agent.",
        annotations=READ_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def get_active_round() -> AgentRoundOutput:
        return await gateway.get_active_round()

    @server.tool(
        description="Return the visible Civarium state for the authenticated agent.",
        annotations=READ_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def get_visible_state() -> VisibleStateOutput:
        return await gateway.get_visible_state()

    @server.tool(
        description=(
            "Submit a command for the authenticated agent. The payload is forwarded as "
            "an opaque object; its required shape depends on command_type and is "
            "validated by the Civarium backend command registry."
        ),
        annotations=WRITE_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def submit_command(
        round_id: RoundIdParam,
        client_command_id: ClientCommandIdParam,
        command_type: CommandTypeParam,
        payload: CommandPayloadParam,
    ) -> CommandReceivedOutput:
        return await gateway.submit_command(
            round_id=round_id,
            client_command_id=client_command_id,
            command_type=command_type,
            payload=payload,
        )

    @server.tool(
        description="List commands accepted for the authenticated agent in a Civarium round.",
        annotations=READ_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def list_my_commands(round_id: RoundIdParam) -> AcceptedCommandListOutput:
        return await gateway.list_my_commands(round_id)

    @server.tool(
        description=(
            "Poll the active round until it changes from after_round_id or a bounded "
            "timeout expires. This never advances the Civarium session."
        ),
        annotations=READ_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def wait_next_round(
        after_round_id: RoundIdParam,
        timeout_seconds: TimeoutParam = 60.0,
    ) -> WaitNextRoundOutput:
        effective_timeout = min(timeout_seconds, config.wait_max_timeout_seconds)

        async with wait_lock:
            loop = asyncio.get_running_loop()
            started_at = loop.time()
            deadline = started_at + effective_timeout

            while True:
                current_round = await gateway.get_active_round()
                elapsed = loop.time() - started_at
                if current_round.round_id != after_round_id:
                    return WaitNextRoundOutput(
                        status="changed",
                        after_round_id=after_round_id,
                        timed_out=False,
                        timeout_seconds=effective_timeout,
                        elapsed_seconds=round(elapsed, 3),
                        round=current_round,
                    )

                remaining = deadline - loop.time()
                if remaining <= 0:
                    return WaitNextRoundOutput(
                        status="timeout",
                        after_round_id=after_round_id,
                        timed_out=True,
                        timeout_seconds=effective_timeout,
                        elapsed_seconds=round(loop.time() - started_at, 3),
                        round=current_round,
                    )

                await asyncio.sleep(min(config.wait_poll_interval_seconds, remaining))
