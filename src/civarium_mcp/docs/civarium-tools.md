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

Current visible entity libraries use `construction` for unfinished building
projects and `structure` for completed buildings. Current visibility is
owner-based in the backend.

## Tool Reference

### `get_civarium_context`

Read-only context tool. It returns the static Civarium overview as Markdown for
MCP clients that expose tools to agents but do not surface MCP resources or
server instructions.

Game meaning: no world state is read or changed. This tool orients the agent to
what Civarium is and how to interpret the MCP server.

Resource-aware clients should prefer reading `civarium://docs/overview`
directly.

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

Current expected entity library keys are `construction` and `structure`.

### `submit_command`

Write tool. It submits a command intent for the authenticated agent in a round.

Game meaning: this is how the agent tries to affect the world. The command is an
intent recorded by the backend, not an immediate state mutation.

Important input:

- `round_id`: active round UUID returned by `get_active_round`;
- `client_command_id`: caller-generated UUID used as the idempotency key;
- `command_type`: backend command handler name;
- `payload`: command-specific action payload.

The current implemented command type is `construction_start`. Its payload uses:

- `title`: building title;
- `rounds_to_complete`: number of rounds before completion.

Important output:

- `command_id`: backend UUID assigned to the submitted command intent;
- `is_valid`: whether backend validation admitted the command for later
  execution;
- `checks`: backend validation feedback.

If `is_valid` is false, the command was received and has a receipt, but it is not
queued for execution.

### `list_my_commands`

Read-only command-history tool. It lists valid commands admitted for execution
for the authenticated agent in a round.

Game meaning: use this to confirm which submitted intents are queued for later
round execution. Invalid submissions can still have receipts, but they are not
included here.

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
2. Call `get_active_round`.
3. Call `get_visible_state`.
4. Reason from the visible state and implemented command surface.
5. Submit a command intent with `submit_command` when action is appropriate.
6. Use `list_my_commands` to confirm which intents were admitted for execution.
7. Use `wait_next_round` when the agent should wait for the next decision
   window, then read visible state again.
