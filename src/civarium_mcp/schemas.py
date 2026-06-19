"""Local MCP input and output schemas for the Civarium adapter."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CivariumContextOutput(BaseModel):
    """Static Civarium context document for MCP clients and agents."""

    uri: str = Field(
        description=(
            "Canonical MCP resource URI for this Civarium reference document. Clients "
            "with resource support should prefer reading this URI directly."
        ),
    )
    title: str = Field(
        description="Human-readable title of the Civarium reference document.",
    )
    mime_type: str = Field(
        description="MIME type of the returned reference document content.",
    )
    content: str = Field(
        description=(
            "Markdown content explaining the high-level Civarium game context, agent "
            "role, world model, and command semantics."
        ),
    )


class CivariumDocSummaryOutput(BaseModel):
    """Metadata for one static Civarium reference document."""

    doc_id: str = Field(
        description=(
            "Stable document id accepted by read_civarium_doc, such as `overview` "
            "or `tools`."
        ),
    )
    uri: str = Field(
        description="Canonical MCP resource URI for this Civarium reference document.",
    )
    title: str = Field(
        description="Human-readable title of the Civarium reference document.",
    )
    mime_type: str = Field(
        description="MIME type of the reference document content.",
    )
    description: str = Field(
        description=(
            "Short explanation of what this document covers and when an agent should "
            "read it."
        ),
    )


class CivariumDocListOutput(BaseModel):
    """List of static Civarium reference documents exposed by this adapter."""

    docs: list[CivariumDocSummaryOutput] = Field(
        description=(
            "Static Civarium docs available through read_civarium_doc and, for "
            "resource-aware clients, the corresponding MCP resource URI."
        ),
    )


class CivariumDocOutput(CivariumDocSummaryOutput):
    """Static Civarium reference document content."""

    content: str = Field(
        description="Markdown content of the requested Civarium reference document.",
    )


class RuleCallableOutput(BaseModel):
    """Public metadata for a callable used by a Civarium rule."""

    name: str = Field(
        description="Python callable name exposed by the Civarium rules catalog.",
    )
    description: str | None = Field(
        default=None,
        description="Docstring-derived explanation of the callable, when available.",
    )


class CommandTypeListOutput(BaseModel):
    """Registered Civarium command types."""

    command_types: list[str] = Field(
        description=(
            "Registered command types accepted by submit_command when paired with a "
            "payload matching the corresponding command spec."
        ),
    )


class CommandTypeSpecOutput(BaseModel):
    """Public specification for one registered Civarium command type."""

    command_type: str = Field(
        description="Registered Civarium command type.",
    )
    description: str | None = Field(
        default=None,
        description="Docstring-derived command payload description, when available.",
    )
    payload_schema: dict[str, Any] = Field(
        description="JSON Schema for the command payload expected by the backend.",
    )
    events: list[str] = Field(
        description=(
            "Event types statically discovered from the command handler. This is "
            "documentation of the current implementation, not a command execution result."
        ),
    )
    validators: list[RuleCallableOutput] = Field(
        description="Validators applied by the backend for this command type.",
    )


class EntityTypeListOutput(BaseModel):
    """Registered Civarium entity types."""

    entity_types: list[str] = Field(
        description="Registered entity types that may appear in visible state snapshots.",
    )


class EntityTypeSpecOutput(BaseModel):
    """Public specification for one registered Civarium entity type."""

    entity_type: str = Field(
        description="Registered Civarium entity type.",
    )
    description: str | None = Field(
        default=None,
        description="Docstring-derived entity description, when available.",
    )
    entity_schema: dict[str, Any] = Field(
        description="JSON Schema for records in this entity library.",
    )


class EventTypeListOutput(BaseModel):
    """Registered Civarium event types."""

    event_types: list[str] = Field(
        description="Registered event types emitted and projected by the backend.",
    )


class EventTypeSpecOutput(BaseModel):
    """Public specification for one registered Civarium event type."""

    event_type: str = Field(
        description="Registered Civarium event type.",
    )
    description: str | None = Field(
        default=None,
        description="Docstring-derived event payload description, when available.",
    )
    payload_schema: dict[str, Any] = Field(
        description="JSON Schema for the event payload expected by the backend.",
    )
    validators: list[RuleCallableOutput] = Field(
        description="Validators applied by the backend for this event type.",
    )
    modificator: RuleCallableOutput = Field(
        description="Projection callable that applies this event to world state.",
    )


class RuleCatalogResourcesOutput(BaseModel):
    """MCP resource URIs for the Civarium rule catalog."""

    catalog_uri: str = Field(
        description="Canonical MCP resource URI for the compact rule catalog index.",
    )
    command_types_uri: str = Field(
        description="MCP resource URI listing registered command types.",
    )
    command_spec_uri_template: str = Field(
        description="MCP resource URI template for one command type specification.",
    )
    entity_types_uri: str = Field(
        description="MCP resource URI listing registered entity types.",
    )
    entity_spec_uri_template: str = Field(
        description="MCP resource URI template for one entity type specification.",
    )
    event_types_uri: str = Field(
        description="MCP resource URI listing registered event types.",
    )
    event_spec_uri_template: str = Field(
        description="MCP resource URI template for one event type specification.",
    )


class RuleCatalogIndexOutput(BaseModel):
    """Compact index of the Civarium rule catalog exposed by the backend."""

    resources: RuleCatalogResourcesOutput = Field(
        description=(
            "Canonical MCP resources and resource templates exposing the same rule "
            "catalog data."
        ),
    )
    command_types: list[str] = Field(
        description="Registered command types.",
    )
    entity_types: list[str] = Field(
        description="Registered entity types.",
    )
    event_types: list[str] = Field(
        description="Registered event types.",
    )


class EntityLibraryOutput(BaseModel):
    """Visible entity library returned by Civarium."""

    next_id: int = Field(
        default=0,
        description=(
            "Next local entity id allocated for this visible entity library. This is "
            "context for interpreting ids within one entity type and is not a command "
            "target by itself."
        ),
    )
    entities: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description=(
            "Visible entity records in this library, keyed by entity id. Record shape "
            "depends on the entity type; use get_civarium_entity_spec or the matching "
            "`civarium://rules/entities/{entity_type}` resource for the current schema."
        ),
    )


class AgentRoundOutput(BaseModel):
    """Active round context visible to the authenticated agent."""

    session_id: UUID = Field(
        description=(
            "Civarium session UUID that owns the active round and scopes the agent's "
            "visible game context."
        ),
    )
    round_id: UUID = Field(
        description=(
            "Active round UUID. Use this value when submitting commands for the current "
            "decision window."
        ),
    )
    round_idx: int = Field(
        description=(
            "Non-negative backend round index used to order rounds within the session."
        ),
    )


class VisibleStateOutput(BaseModel):
    """Visible game state for the authenticated agent."""

    round_id: UUID = Field(
        description="Round UUID for which this visible state snapshot was produced.",
    )
    entities: dict[str, EntityLibraryOutput] = Field(
        default_factory=dict,
        description=(
            "Dictionary of visible entity libraries by entity type. Use "
            "list_civarium_entity_types or `civarium://rules/entities` to discover "
            "currently registered entity types; only entities visible to the "
            "authenticated agent are included."
        ),
    )


class CommandReceivedOutput(BaseModel):
    """Backend receipt for a submitted command."""

    command_id: UUID = Field(
        description="Backend UUID assigned to the submitted command intent.",
    )
    round_id: UUID = Field(
        description="Round UUID in which the backend received and evaluated the command.",
    )
    client_command_id: UUID = Field(
        description=(
            "Caller-provided UUID echoed back so the agent can match the receipt to its "
            "original command intent."
        ),
    )
    is_valid: bool = Field(
        description=(
            "Whether backend validation admitted the command for later round execution. "
            "False means the command was received and has a receipt, but it is not queued "
            "for execution."
        ),
    )
    checks: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Backend validation results keyed by rule or check name. Values explain "
            "accepted constraints or validation failures for the submitted command. Use "
            "get_civarium_command_spec for command validator metadata."
        ),
    )


class AcceptedCommandOutput(BaseModel):
    """Valid submitted command queued for the authenticated agent in a round."""

    command_id: UUID = Field(
        description="Backend UUID of a valid submitted command queued for this agent.",
    )
    client_command_id: UUID = Field(
        description="Caller-generated UUID originally supplied with the command intent.",
    )
    command_type: str = Field(
        description=(
            "Civarium command type that selected the backend command handler. Discover "
            "currently registered values with list_civarium_command_types."
        ),
    )
    payload: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Command-specific payload accepted by the backend. Shape depends on "
            "command_type and mirrors the agent's submitted intent; use "
            "get_civarium_command_spec for the current payload schema."
        ),
    )
    created_at: datetime = Field(
        description="Timestamp at which the backend recorded the command intent.",
    )


class AcceptedCommandListOutput(BaseModel):
    """Valid submitted commands queued for the authenticated agent in one round."""

    round_id: UUID = Field(
        description="Round UUID whose accepted submitted commands are listed.",
    )
    commands: list[AcceptedCommandOutput] = Field(
        default_factory=list,
        description=(
            "Valid submitted commands admitted for later execution for the authenticated "
            "agent in this round. These are queued intents, not available command types "
            "and not proof that world state has changed yet; invalid submissions may "
            "have receipts but are not included here."
        ),
    )


class WaitNextRoundOutput(BaseModel):
    """Structured result for bounded next-round polling."""

    status: Literal["changed", "timeout"] = Field(
        description=(
            "`changed` when the active round differs from after_round_id; `timeout` when "
            "the bounded wait expired first."
        ),
    )
    after_round_id: UUID = Field(
        description="Previously observed active round UUID that the polling wait compared against.",
    )
    timed_out: bool = Field(
        description="True when polling ended because the timeout expired before a round change.",
    )
    timeout_seconds: float = Field(
        description=(
            "Effective maximum seconds used for this wait after adapter limits were "
            "applied."
        ),
    )
    elapsed_seconds: float = Field(
        description="Measured seconds spent polling before returning this result.",
    )
    round: AgentRoundOutput | None = Field(
        default=None,
        description=(
            "Current active round observed at the end of polling. Present on both changed "
            "and timeout results when the backend returned a round; on timeout it is "
            "usually still after_round_id."
        ),
    )
