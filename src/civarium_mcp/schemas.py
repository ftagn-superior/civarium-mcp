"""Local MCP input and output schemas for the Civarium adapter."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class EntityLibraryOutput(BaseModel):
    """Visible entity library returned by Civarium."""

    next_id: int = 0
    entities: dict[str, dict[str, Any]] = Field(default_factory=dict)


class AgentRoundOutput(BaseModel):
    """Active round context visible to the authenticated agent."""

    session_id: UUID
    round_id: UUID
    round_idx: int


class VisibleStateOutput(BaseModel):
    """Visible game state for the authenticated agent."""

    round_id: UUID
    entities: dict[str, EntityLibraryOutput] = Field(default_factory=dict)


class CommandReceivedOutput(BaseModel):
    """Backend receipt for a submitted command."""

    command_id: UUID
    round_id: UUID
    client_command_id: UUID
    is_valid: bool
    checks: dict[str, str] = Field(default_factory=dict)


class AcceptedCommandOutput(BaseModel):
    """Command accepted for the authenticated agent in a round."""

    command_id: UUID
    client_command_id: UUID
    command_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AcceptedCommandListOutput(BaseModel):
    """Accepted commands for the authenticated agent in one round."""

    round_id: UUID
    commands: list[AcceptedCommandOutput] = Field(default_factory=list)


class WaitNextRoundOutput(BaseModel):
    """Structured result for bounded next-round polling."""

    status: Literal["changed", "timeout"]
    after_round_id: UUID
    timed_out: bool
    timeout_seconds: float
    elapsed_seconds: float
    round: AgentRoundOutput | None = None
