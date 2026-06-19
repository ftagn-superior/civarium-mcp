# Civarium Agent Tools

This document describes the MCP tools exposed by the Civarium adapter and how an
agent should understand them inside the game world. It complements
`civarium://docs/overview`, which explains the game context at a higher level.

The tools are the authenticated agent's player-facing interface to Civarium.
They are not admin APIs and they do not expose hidden world state. The bearer
token selects the agent identity, so tools do not ask the caller to provide
`agent_id` or `session_id`.

## Shared Semantics

Civarium is turn-based. The active round is the current decision window for the
agent. Reading tools provide the state the agent can currently observe. Writing
tools submit command intents to the backend.

Submitting a command does not immediately mutate the world. A command is
recorded, validated, and, if accepted, queued for later execution when the round
advances. Later visible state snapshots are the source of truth for world
changes.

The runtime rules catalog is the source of truth for currently registered
command types, payload schemas, entity types, entity schemas, event types,
validators, and projection metadata.

## Tool Reference

### `get_civarium_context`

Read-only context tool. It returns the static Civarium overview as Markdown for
MCP clients that expose tools to agents but do not surface MCP resources or
server instructions.

Game meaning: no world state is read or changed. This tool orients the agent to
what Civarium is and how to interpret the MCP server.

Resource-aware clients should prefer reading `civarium://docs/overview`
directly.

### `list_civarium_docs`

Read-only documentation tool. It lists the packaged Civarium Markdown documents
available through tool calls and MCP resources.

Game meaning: no world state is read or changed. Use this when the client does
not expose MCP resource discovery to the agent.

### `read_civarium_doc`

Read-only documentation tool. It reads one packaged Civarium Markdown document
by `doc_id`.

Game meaning: no world state is read or changed. This is a tool fallback for
clients that do not expose MCP resource reads.

### `get_civarium_rule_catalog`

Read-only rules tool. It returns a compact index of the registered command,
entity, and event types reported by the backend rules catalog.

Game meaning: this reads the current implemented rule surface. It does not read
hidden state and does not execute rules.

Important output:

- `command_types`: command types accepted by the backend command registry;
- `entity_types`: entity library types that visible state may contain;
- `event_types`: event types registered by the projection pipeline;
- `resources`: canonical `civarium://rules/...` resource URIs for the same
  catalog.

Resource-aware clients can read `civarium://rules/catalog` directly.

### `list_civarium_command_types`

Read-only rules tool. It lists command types currently registered by the
backend.

Use `get_civarium_command_spec` before submitting an unfamiliar command type.

### `get_civarium_command_spec`

Read-only rules tool. It reads one command type specification.

Important output:

- `payload_schema`: JSON Schema for the command payload;
- `events`: event types statically discovered from the command handler;
- `validators`: backend validator metadata.

Resource-aware clients can read
`civarium://rules/commands/{command_type}` directly.

### `list_civarium_entity_types`

Read-only rules tool. It lists entity types currently registered by the backend.

### `get_civarium_entity_spec`

Read-only rules tool. It reads one entity type specification, including the JSON
Schema for records in that entity library.

Resource-aware clients can read `civarium://rules/entities/{entity_type}`
directly.

### `list_civarium_event_types`

Read-only rules tool. It lists event types currently registered by the backend.
Agents cannot submit events directly.

### `get_civarium_event_spec`

Read-only rules tool. It reads one event type specification.

Important output:

- `payload_schema`: JSON Schema for the event payload;
- `validators`: backend validator metadata;
- `modificator`: projection callable metadata.

Resource-aware clients can read `civarium://rules/events/{event_type}` directly.

### `get_active_round`

Read-only game-state tool. It returns the active Civarium round for the
authenticated agent.

Game meaning: this identifies the current decision window. Use its `round_id`
when submitting commands for the current round.

Important output:

- `session_id`: backend session UUID that scopes the active round;
- `round_id`: active round UUID for command submission;
- `round_idx`: backend round index within the session.

### `get_visible_state`

Read-only game-state tool. It returns the authenticated agent's visible slice of
the Civarium world.

Game meaning: this is what the agent can currently observe. Hidden state, unseen
entities, and other agents' private information are not included.

Important output:

- `round_id`: round UUID for the visible state snapshot;
- `entities`: visible entity libraries keyed by entity type.

Use `list_civarium_entity_types` and `get_civarium_entity_spec` to inspect the
current entity catalog.

### `submit_command`

Write tool. It submits a command intent for the authenticated agent in a round.

Game meaning: this is how the agent tries to affect the world. The command is an
intent recorded by the backend, not an immediate state mutation.

Important input:

- `round_id`: active round UUID returned by `get_active_round`;
- `client_command_id`: caller-generated UUID used as the idempotency key;
- `command_type`: backend command handler name;
- `payload`: command-specific action payload.

Use `list_civarium_command_types` and `get_civarium_command_spec` to inspect the
current command catalog and payload schema before submitting.

Important output:

- `command_id`: backend UUID assigned to the submitted command intent;
- `is_valid`: whether backend validation admitted the command for later
  execution;
- `checks`: backend validation feedback.

If `is_valid` is false, the command was received and has a receipt, but it is not
queued for execution.

### `list_queued_submitted_commands`

Read-only command-history tool. It lists submitted command intents that the
backend has validated and queued for execution for the authenticated agent in a
round.

Game meaning: use this to confirm which submitted intents are queued for later
round execution. This is not a catalog of available command types. Invalid
submissions can still have receipts, but they are not included here.

Important input:

- `round_id`: round UUID whose accepted commands should be listed.

Important output:

- `commands`: valid queued command intents for that round.

### `wait_next_round`

Read-only polling tool. It waits for the active round to change from a previously
observed round id or until a bounded timeout expires.

Game meaning: this lets the agent wait for session progress. It does not advance
the Civarium session and does not execute commands by itself.

Important input:

- `after_round_id`: active round UUID already observed by the agent;
- `timeout_seconds`: maximum seconds to wait, capped by adapter configuration.

Important output:

- `status`: `changed` when the active round changed, or `timeout` when polling
  expired first;
- `round`: active round observed at the end of polling, when available.

## Suggested Decision Loop

1. Read `civarium://docs/overview` and this document if the client supports MCP
   resources. If not, call `get_civarium_context` for the high-level overview.
2. Call `get_civarium_rule_catalog`, or read `civarium://rules/catalog`, when
   you need the live command, entity, or event catalog.
3. Call `get_active_round`.
4. Call `get_visible_state`.
5. Reason from the visible state and implemented command surface.
6. Read the relevant command spec before constructing a new command payload.
7. Submit a command intent with `submit_command` when action is appropriate.
8. Use `list_queued_submitted_commands` to confirm which intents were admitted
   for execution.
9. Use `wait_next_round` when the agent should wait for the next decision
   window, then read visible state again.
