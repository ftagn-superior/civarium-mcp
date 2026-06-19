# Civarium Glossary

This glossary stabilizes terms used by Civarium MCP resources, tools, and
agent-facing schemas.

## Implemented

### Agent

The player-controlled actor represented by the authenticated bearer token. MCP
tools expose the view and actions of this agent.

### Session

One Civarium game instance. Agents, rounds, commands, events, and state snapshots
belong to a session.

### Round

A decision window within a session. Commands are submitted for a specific round.

### Active Round

The round currently open for agent decisions. `get_active_round` returns the
active round for the authenticated agent.

### Visible State

The agent's observable state snapshot returned by `get_visible_state`. It is a
filtered perspective, not the complete hidden world.

### Hidden State

World information not visible to the authenticated agent. Hidden state includes
unseen entities, other agents' private information, and backend facts not
exposed through the agent surface.

### Rule Catalog

The read-only backend catalog of registered command, entity, and event specs.
Use `get_civarium_rule_catalog` or `civarium://rules/catalog` as the entry point.

### Command Type

A registered command handler name accepted by `submit_command`. Discover current
values with `list_civarium_command_types` or `civarium://rules/commands`, and
inspect payload schemas with `get_civarium_command_spec` or
`civarium://rules/commands/{command_type}`.

### Entity Type

A registered visible-state library key. Discover current values with
`list_civarium_entity_types` or `civarium://rules/entities`, and inspect record
schemas with `get_civarium_entity_spec` or
`civarium://rules/entities/{entity_type}`.

### Event Type

A registered backend event kind. Discover current values with
`list_civarium_event_types` or `civarium://rules/events`, and inspect payload
schemas and projection metadata with `get_civarium_event_spec` or
`civarium://rules/events/{event_type}`.

### Entity Library

A collection of visible entities of one type inside visible state. The runtime
rules catalog provides the current entity type list and schemas.

### Command Intent

An agent's requested action submitted through `submit_command`. A command intent
is not an immediate world mutation.

### Receipt

The backend response returned by `submit_command`. It reports command intake,
validation result, and checks.

### Validation Check

A backend validation result entry returned in a receipt's `checks` object.
Checks explain accepted constraints or validation failures.

### Queued Command

A valid submitted command admitted for later execution in a round.
`list_queued_submitted_commands` returns valid queued submitted commands for the
authenticated agent and round; it does not list available command types.

### Event

A backend record of something that changes or advances world state. Commands can
produce events during round advancement. The runtime rules catalog provides the
current event type list and specs.

### Projection

The process of applying valid events to produce a new world state snapshot.
Agents observe projected results through later visible state snapshots.

## Design Direction

Future Civarium mechanics may add new terms. A term should not be treated as an
implemented mechanic until it is exposed through the agent-facing gameplay tools
or the runtime rules catalog.
