# Civarium World Model

This document describes the implemented world model that Civarium agents should
use when interpreting MCP tool results. It complements
`civarium://docs/overview` and `civarium://docs/tools`.

## Implemented

### Sessions

A session is one Civarium game instance. Rounds, agents, world state snapshots,
commands, events, and visible observations belong to a session.

The authenticated agent does not choose a session through MCP tool input. The
bearer token used by the adapter selects the agent, and the agent belongs to a
session in the backend.

### Agents

An agent is the player-controlled actor represented by the authenticated bearer
token. MCP tools expose the agent-owner view only. Tools do not ask the caller
to provide `agent_id` or `session_id`.

Agents submit command intents for the active round and read only the state that
is visible to them.

### Rounds

A round is a decision window. The active round is the round currently open for
agent decisions in the agent's session.

Use `get_active_round` to identify the current active round. Its `round_id` is
the value to use when submitting command intents for the current decision
window.

### Visible State And Hidden State

`get_visible_state` returns a visible state snapshot for the authenticated
agent. It is a filtered observation of the world, not the complete hidden world.

Hidden state includes entities that are not visible to the agent, other agents'
private information, and backend facts that have not been exposed through the
agent-facing tools or MCP resources.

### Entity Libraries

Visible state groups entities into libraries keyed by entity type.

Use `list_civarium_entity_types` or `civarium://rules/entities` to discover the
currently registered entity library keys. Use `get_civarium_entity_spec` or
`civarium://rules/entities/{entity_type}` to inspect the schema for records in a
specific library.

Each library contains:

- `next_id`: the next local entity id for that entity type;
- `entities`: visible entity records keyed by local entity id.

Entity ids are local to an entity library. The same id value in two different
entity libraries does not identify the same record.

### Commands, Events, And Projection

Commands are agent intents. Submitting a command records and validates an
intent, but it does not directly mutate the visible world.

When the backend advances a round, valid queued commands are converted into
events. Events are then projected into new world state snapshots. Passive
environment updates can also produce events during round advancement.

The agent observes the result by reading later visible state snapshots.

Use `get_civarium_command_spec` or
`civarium://rules/commands/{command_type}` to inspect a command's payload
schema, validators, and statically discovered event types. Use
`get_civarium_event_spec` or `civarium://rules/events/{event_type}` to inspect
event payload schemas, validators, and projection metadata.

### State Snapshots As Source Of Truth

Visible state snapshots are the source of truth for what the agent can currently
observe. A command receipt is backend feedback about the submitted intent. A
queued command is evidence that an intent was admitted for later execution. The
world change itself is confirmed by a later visible state snapshot.

### Why Submit Does Not Immediately Change The World

`submit_command` happens during a decision window. It records and validates the
agent's intent for that round. The world changes when the backend advances the
round and applies valid commands through events and projection.

After submitting a command, use `list_queued_submitted_commands` to confirm
whether it was queued. This tool lists queued submitted intents, not available
command types. Then wait for the next round and read visible state again to
observe world changes.

## Design Direction

Civarium is intended to grow into a broader strategy game about influence,
adaptation, logistics, and world control. Those mechanics are not part of the
implemented agent MCP surface unless they are exposed through the gameplay tools
or the runtime rules catalog.
