# Civarium Command Lifecycle

This document explains how a command intent moves through the current Civarium
agent MCP surface.

## Implemented

### 1. Draft An Intent

The agent first reads the current decision context:

1. Call `get_active_round`.
2. Call `get_visible_state`.
3. Decide whether an implemented command is appropriate.

For a new command intent, generate a fresh `client_command_id` UUID. Reuse a
`client_command_id` only when retrying the exact same intent.

### 2. Submit The Intent

Call `submit_command` with:

- `round_id`: the active round id returned by `get_active_round`;
- `client_command_id`: the caller-generated idempotency UUID;
- `command_type`: the command handler name;
- `payload`: command-specific intent data.

The current implemented command type is `construction_start`.

### 3. Backend Intake And Validation

The backend receives the command intent for the authenticated agent. It checks
that the submitted round is still the active round and validates the command
payload against the current backend command handler.

For `construction_start`, the current payload fields are:

- `title`: building title;
- `rounds_to_complete`: number of rounds before completion.

Current construction validation is minimal and primarily confirms the typed
payload shape.

### 4. Receipt

`submit_command` returns a receipt with:

- `command_id`: backend UUID assigned to this command intent;
- `round_id`: round in which the command was received;
- `client_command_id`: caller idempotency UUID echoed back;
- `is_valid`: whether validation admitted the command for later execution;
- `checks`: validation feedback keyed by backend check name.

The receipt is not a world state snapshot.

### 5. Invalid Receipt

If `is_valid` is false, the backend received the command and returned a receipt,
but the command is not queued for execution. The agent should inspect `checks`
and decide whether to submit a corrected new intent.

Invalid submissions may have receipts, but they are not returned by
`list_my_commands`.

### 6. Valid Queued Command

If `is_valid` is true, the command was admitted for later execution in the round.
Use `list_my_commands(round_id)` to confirm valid queued commands for the
authenticated agent in that round.

A valid queued command is still an intent waiting for round advancement. It is
not proof that the world has already changed.

### 7. Round Advancement

The MCP adapter does not advance the session. `wait_next_round` only polls until
the active round changes or a bounded timeout expires.

When the backend advances a round, valid queued commands are executed by backend
systems. Command execution emits events, and projection applies valid events to
produce new state snapshots.

### 8. Resulting Visible State

After the active round changes, call `get_visible_state` again. The returned
visible state snapshot is the agent's observable result of all executed commands
and passive environment updates that affected visible entities.

### Invalid Receipt Vs Valid Queued Command

An invalid receipt means:

- the backend received the intent;
- validation did not admit it;
- it is not queued for execution;
- it should not appear in `list_my_commands`.

A valid queued command means:

- the backend received the intent;
- validation admitted it;
- it can appear in `list_my_commands`;
- it will affect the world only when the round advances and backend execution
  produces projected state.

## Design Direction

Future command types may add richer validation and more detailed checks. Agents
should continue to treat receipts as intake feedback and visible state snapshots
as the source of truth for observed world changes.
