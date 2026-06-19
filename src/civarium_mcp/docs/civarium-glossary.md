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

### Entity Library

A collection of visible entities of one type inside visible state. Current
implemented entity libraries are `construction` and `structure`.

### Construction

An unfinished building project. Current visible fields are `owner`, `title`, and
`rounds_to_complete`.

### Structure

A completed building. Current visible fields are `owner` and `title`.

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
produce events during round advancement.

### Projection

The process of applying valid events to produce a new world state snapshot.
Agents observe projected results through later visible state snapshots.

## Design Direction

Future Civarium mechanics may add new terms. A term should not be treated as an
implemented mechanic until a Civarium document marks it as implemented and the
agent-facing tools expose it.
