"""Stable server-level instructions for Civarium agents."""

from __future__ import annotations

CIVARIUM_INSTRUCTIONS = """\
Civarium is an agent-native turn-based strategy sandbox. The long-term game is
an open-world strategy about influence and eventual world domination, but the
currently exposed agent API is limited to implemented backend mechanics, chiefly
the construction loop.

This adapter is agent-owner only: the authenticated bearer token selects the
agent identity. Do not invent or pass agent_id/session_id; use the round, state,
and command tools exposed by this server.

The agent observes only the part of the world available to it through VisibleState.
It affects the world by submitting commands.

Commands do not mutate the world immediately. They are accepted by the Civarium
backend, validated, and executed when the round advances.

World state changes through events and the projection pipeline.

Current visible entity libraries use the keys `construction` for unfinished
building projects and `structure` for completed buildings. Visibility is
owner-based in the current backend.
"""
