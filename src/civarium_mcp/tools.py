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
    rule_catalog_resources,
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
    CommandTypeListOutput,
    CommandTypeSpecOutput,
    EntityTypeListOutput,
    EntityTypeSpecOutput,
    EventTypeListOutput,
    EventTypeSpecOutput,
    RuleCatalogIndexOutput,
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
            "Civarium command type to submit. Use list_civarium_command_types and "
            "get_civarium_command_spec to discover currently registered values and "
            "their expected payload shapes."
        ),
    ),
]
CommandPayloadParam = Annotated[
    dict[str, Any],
    Field(
        description=(
            "Command-specific payload describing the agent's intended game action. Shape "
            "depends on command_type and is validated by the Civarium backend command "
            "registry; inspect get_civarium_command_spec before submitting an unfamiliar "
            "command type."
        ),
    ),
]
RuleCommandTypeParam = Annotated[
    str,
    Field(
        description=(
            "Registered Civarium command type to inspect. Use list_civarium_command_types "
            "or get_civarium_rule_catalog to discover available values."
        ),
    ),
]
RuleEntityTypeParam = Annotated[
    str,
    Field(
        description=(
            "Registered Civarium entity type to inspect. Use list_civarium_entity_types "
            "or get_civarium_rule_catalog to discover available values."
        ),
    ),
]
RuleEventTypeParam = Annotated[
    str,
    Field(
        description=(
            "Registered Civarium event type to inspect. Use list_civarium_event_types "
            "or get_civarium_rule_catalog to discover available values."
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


async def _rule_catalog_index(gateway: HttpCivariumGateway) -> RuleCatalogIndexOutput:
    command_types, entity_types, event_types = await asyncio.gather(
        gateway.list_command_types(),
        gateway.list_entity_types(),
        gateway.list_event_types(),
    )
    return RuleCatalogIndexOutput(
        resources=rule_catalog_resources(),
        command_types=command_types.command_types,
        entity_types=entity_types.entity_types,
        event_types=event_types.event_types,
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
            "Return a compact JSON index of the current Civarium rules catalog from the "
            "backend: registered command, entity, and event types plus the canonical MCP "
            "resource URIs for reading the same catalog through resources."
        ),
        annotations=READ_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def get_civarium_rule_catalog() -> RuleCatalogIndexOutput:
        return await _rule_catalog_index(gateway)

    @server.tool(
        description=(
            "List command types currently registered by the Civarium backend. Use "
            "get_civarium_command_spec for the payload schema before submit_command."
        ),
        annotations=READ_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def list_civarium_command_types() -> CommandTypeListOutput:
        return await gateway.list_command_types()

    @server.tool(
        description=(
            "Read the backend rules catalog specification for one command type, including "
            "payload JSON Schema, validators, and statically discovered emitted event types."
        ),
        annotations=READ_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def get_civarium_command_spec(
        command_type: RuleCommandTypeParam,
    ) -> CommandTypeSpecOutput:
        return await gateway.get_command_spec(command_type)

    @server.tool(
        description=(
            "List entity types currently registered by the Civarium backend. These are "
            "the entity library keys that visible state snapshots may contain."
        ),
        annotations=READ_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def list_civarium_entity_types() -> EntityTypeListOutput:
        return await gateway.list_entity_types()

    @server.tool(
        description=(
            "Read the backend rules catalog specification for one entity type, including "
            "the JSON Schema for records in that entity library."
        ),
        annotations=READ_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def get_civarium_entity_spec(
        entity_type: RuleEntityTypeParam,
    ) -> EntityTypeSpecOutput:
        return await gateway.get_entity_spec(entity_type)

    @server.tool(
        description=(
            "List event types currently registered by the Civarium backend. Events are "
            "backend facts projected into world state; agents cannot submit them directly."
        ),
        annotations=READ_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def list_civarium_event_types() -> EventTypeListOutput:
        return await gateway.list_event_types()

    @server.tool(
        description=(
            "Read the backend rules catalog specification for one event type, including "
            "payload JSON Schema, validators, and projection modificator metadata."
        ),
        annotations=READ_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def get_civarium_event_spec(
        event_type: RuleEventTypeParam,
    ) -> EventTypeSpecOutput:
        return await gateway.get_event_spec(event_type)

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
            "Use list_civarium_entity_types and get_civarium_entity_spec to inspect "
            "currently registered entity libraries."
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
            "immediate mutation of the world. Use get_civarium_command_spec to inspect "
            "the payload schema before submitting a command type."
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
            "List submitted command intents that the backend has validated and queued "
            "for later execution for the authenticated agent in a Civarium round. Use "
            "this after submit_command to confirm which submitted intents are queued; "
            "this does not list available command types. Invalid submissions can still "
            "have receipts but are not listed here."
        ),
        annotations=READ_TOOL_ANNOTATIONS,
        structured_output=True,
    )
    async def list_queued_submitted_commands(
        round_id: RoundIdParam,
    ) -> AcceptedCommandListOutput:
        return await gateway.list_queued_submitted_commands(round_id)

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
