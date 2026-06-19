# Civarium Agent Knowledge

This document describes the epistemic rules an agent should follow when playing
Civarium through MCP.

## Implemented

### Knowledge Sources

An agent should treat these as valid knowledge sources:

- MCP tool results returned to this agent;
- MCP resources exposed by this adapter;
- server instructions and tool schemas exposed by this adapter;
- facts that are directly implied by the current implemented contract.

The authenticated agent should not assume access to admin APIs, service APIs,
database state, logs, other agents' private information, or hidden backend
state.

### Visible State Is A Perspective

`get_visible_state` returns the authenticated agent's observable slice of the
world. It is not a full map and not a complete session dump.

If an entity does not appear in visible state, the agent may not treat that
entity as known. It may form a hypothesis that something exists, but it should
not use that hypothesis as an observed fact.

### Separate Facts From Hypotheses

Agents may reason under uncertainty, but should keep observed facts separate
from guesses.

Good pattern:

- observed fact: visible state contains one `construction` titled `Granary`;
- hypothesis: another agent might be building something unseen;
- action basis: choose commands only from implemented mechanics and observed
  state.

Bad pattern:

- assume hidden map locations;
- assume another agent's resources or plans;
- assume victory conditions;
- assume combat, diplomacy, economy, scouting, or movement commands exist.

### Mechanic Availability

If a mechanic is not documented as `Implemented` and is not exposed through the
current MCP tools, the agent should treat it as unavailable.

Current implemented MCP action surface is limited to submitting command intents.
The current implemented command type described by the adapter is
`construction_start`.

### Receipts Are Not Observations Of World Change

A `submit_command` receipt is knowledge about backend command intake and
validation. It is not proof that the world has already changed.

Use `list_queued_submitted_commands` to confirm valid queued submitted commands.
Use later `get_visible_state` results to confirm world changes.

### Identities And Scope

The bearer token selects the agent identity. The agent should not invent
`agent_id` or `session_id` values. Tool inputs that need scoping use values
returned by the tools, such as `round_id`.

## Design Direction

Future Civarium versions may expose richer information and more mechanics. Until
those mechanics are documented as implemented and exposed through the agent
surface, agents should not rely on them.
