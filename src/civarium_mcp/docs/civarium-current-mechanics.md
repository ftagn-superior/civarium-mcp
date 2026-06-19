# Civarium Current Mechanics

This document explains how an agent should discover the current implemented
Civarium mechanics. It intentionally does not copy command, entity, or event
specifications that are already exposed by the backend rules catalog.

## Implemented

### Discovery Loop

Use this loop when deciding what mechanics are available:

1. Read `get_civarium_rule_catalog` or `civarium://rules/catalog`.
2. Read command specs with `get_civarium_command_spec` or
   `civarium://rules/commands/{command_type}` before constructing payloads.
3. Read entity specs with `get_civarium_entity_spec` or
   `civarium://rules/entities/{entity_type}` before interpreting entity records.
4. Read event specs with `get_civarium_event_spec` or
   `civarium://rules/events/{event_type}` when reasoning about emitted events
   and projection metadata.
5. Read the active round with `get_active_round`.
6. Read visible state with `get_visible_state`.
7. Submit a registered command intent with `submit_command` when appropriate.
8. Confirm valid queued submitted commands with `list_queued_submitted_commands`.
9. Wait for the active round to change with `wait_next_round`.
10. Read visible state again to observe resulting changes.

### Rule Catalog Boundary

The rules catalog is the source of truth for:

- available command types;
- command payload schemas;
- command validators and statically discovered event types;
- available entity types;
- entity record schemas;
- available event types;
- event payload schemas, validators, and projection metadata.

Static Markdown docs explain how to use those facts. They should not be treated
as a snapshot of the current rule registry.

### Availability Rule

A mechanic is available to the agent only when it is exposed through the MCP
gameplay tools or the runtime rules catalog. Do not infer extra actions from the
long-term game theme, from names that appear in examples, or from hidden backend
concepts.

Visible state is still a limited observation. It should not be treated as a full
session dump.

## Design Direction

Civarium's long-term direction includes a broader strategy game. This document
does not define those future mechanics. It describes how agents should discover
and constrain themselves to the mechanics currently exposed by the MCP adapter
and backend rules catalog.
