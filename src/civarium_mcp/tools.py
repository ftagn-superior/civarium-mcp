"""MCP tool registrations for Civarium."""

from __future__ import annotations

import asyncio
from typing import Annotated, Any, Literal
from uuid import UUID

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from civarium_mcp.config import AdapterConfig
from civarium_mcp.gateway import HttpCivariumGateway
from civarium_mcp.resources import (
    OVERVIEW_MIME_TYPE,
    OVERVIEW_RESOURCE_TITLE,
    OVERVIEW_RESOURCE_URI,
    CivariumDocReference,
    get_civarium_doc,
    load_civarium_doc,
    load_civarium_overview,
)
from civarium_mcp.resources import (
    list_civarium_docs as list_civarium_doc_references,
)
from civarium_mcp.schemas import (
    AcceptedCommandListOutput,
    AgentRoundOutput,
    CivariumContextOutput,
    CivariumDocListOutput,
    CivariumDocOutput,
    CivariumDocSummaryOutput,
    CommandReceivedOutput,
    VisibleStateOutput,
    WaitNextRoundOutput,
)

RoundIdParam = Annotated[
    UUID,
    Field(
        description=(
            "Civarium round UUID returned by get_active_round; scopes one agent "
            "decision window or valid command history."
        ),
    ),
]
AfterRoundIdParam = Annotated[
    UUID,
    Field(
        description=(
            "Active round UUID already observed by the agent; the tool waits until the "
            "active round changes from this value."
        ),
    ),
]
ClientCommandIdParam = Annotated[
    UUID,
    Field(
        description=(
            "Caller-generated UUID used as the idempotency key for one submitted command "
            "intent; choose a fresh value for each new intent and reuse it only when "
            "retrying the same intent."
        ),
    ),
]
CommandTypeParam = Annotated[
    str,
    Field(
        description=(
            "Civarium command type to submit, for example `construction_start`; this "
            "selects the backend command handler and expected payload shape. The current "
            "implemented command type is `construction_start`."
        ),
    ),
]
CommandPayloadParam = Annotated[
    dict[str, Any],
    Field(
        description=(
            "Command-specific payload describing the agent's intended game action. Shape "
            "depends on command_type and is validated by the Civarium backend command "
            "registry. For `construction_start`, send `title` and `rounds_to_complete`."
        ),
    ),
]
TimeoutParam = Annotated[
    float,
    Field(
        gt=0,
        description=(
            "Maximum seconds to wait for the active round to change; capped by adapter "
            "config and never used to advance the session."
        ),
    ),
]
DocIdParam = Annotated[
    Literal[
        "overview",
        "tools",
        "world-model",
        "agent-knowledge",
        "command-lifecycle",
        "current-mechanics",
        "glossary",
    ],
    Field(
        description=(
            "Static Civarium document id to read. Use list_civarium_docs first when "
            "discovering available documentation."
        ),
    ),
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


def _doc_summary(doc: CivariumDocReference) -> CivariumDocSummaryOutput:
    return CivariumDocSummaryOutput(
        doc_id=doc.doc_id,
        uri=doc.uri,
        title=doc.title,
        mime_type=doc.mime_type,
        description=doc.description,
    )


def register_tools(
    server: FastMCP,
    *,
    gateway: HttpCivariumGateway,
    config: AdapterConfig,
) -> None:
    """Register player-facing Civarium tools."""
    wait_lock = asyncio.Lock()

    @server.tool(
        description=(
            "Return the static Civarium overview as Markdown. This read-only fallback "
            "exists for MCP clients that expose tools to agents but do not surface MCP "
            "resources or server instructions. Prefer the `civarium://docs/overview` "
            "resource when resource reading is available."
        ),
        annotations=READ_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def get_civarium_context() -> CivariumContextOutput:
        return CivariumContextOutput(
            uri=OVERVIEW_RESOURCE_URI,
            title=OVERVIEW_RESOURCE_TITLE,
            mime_type=OVERVIEW_MIME_TYPE,
            content=load_civarium_overview(),
        )

    @server.tool(
        description=(
            "List the static Civarium Markdown documents available to the authenticated "
            "agent. Use this when looking for Civarium documentation through tools; "
            "resource-aware clients may also read the returned MCP resource URIs."
        ),
        annotations=READ_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def list_civarium_docs() -> CivariumDocListOutput:
        return CivariumDocListOutput(
            docs=[_doc_summary(doc) for doc in list_civarium_doc_references()],
        )

    @server.tool(
        description=(
            "Read one static Civarium Markdown document by doc_id. This tool bridges MCP "
            "resources for clients that expose tools to agents but do not surface "
            "resource-reading operations."
        ),
        annotations=READ_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def read_civarium_doc(doc_id: DocIdParam) -> CivariumDocOutput:
        doc = get_civarium_doc(doc_id)
        return CivariumDocOutput(
            **_doc_summary(doc).model_dump(),
            content=load_civarium_doc(doc.doc_id),
        )

    @server.tool(
        description=(
            "Return the active Civarium round for the authenticated agent. Use this to "
            "know which round is currently open for the agent's decisions."
        ),
        annotations=READ_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def get_active_round() -> AgentRoundOutput:
        return await gateway.get_active_round()

    @server.tool(
        description=(
            "Return the visible Civarium state for the authenticated agent. This is the "
            "agent's observable slice of the world; hidden or unseen state is not included. "
            "Current entity libraries include `construction` and `structure`."
        ),
        annotations=READ_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def get_visible_state() -> VisibleStateOutput:
        return await gateway.get_visible_state()

    @server.tool(
        description=(
            "Submit a command intent for the authenticated agent in a round. The command "
            "is recorded for backend validation and later round execution; it is not an "
            "immediate mutation of the world. The current implemented command type is "
            "`construction_start`, with payload fields `title` and `rounds_to_complete`."
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
        description=(
            "List valid commands admitted for execution for the authenticated agent in a "
            "Civarium round. Use this to confirm which command intents are queued for "
            "that round; invalid submissions can still have receipts but are not listed "
            "here."
        ),
        annotations=READ_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def list_my_commands(round_id: RoundIdParam) -> AcceptedCommandListOutput:
        return await gateway.list_my_commands(round_id)

    @server.tool(
        description=(
            "Wait for the active round to change from after_round_id or until a bounded "
            "timeout expires. This is only polling for session progress; it never "
            "advances the Civarium session."
        ),
        annotations=READ_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def wait_next_round(
        after_round_id: AfterRoundIdParam,
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
