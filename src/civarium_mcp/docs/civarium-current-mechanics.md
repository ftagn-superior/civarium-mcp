# Civarium Current Mechanics

This document intentionally describes only the current implemented Civarium
agent MCP reality. It should keep agents inside the mechanics that exist now.

## Implemented

### Current Loop

The current implemented loop is a construction loop:

1. Read the active round with `get_active_round`.
2. Read visible state with `get_visible_state`.
3. Submit a `construction_start` command intent when appropriate.
4. Confirm valid queued commands with `list_my_commands`.
5. Wait for the active round to change with `wait_next_round`.
6. Read visible state again to observe resulting changes.

### Command: `construction_start`

`construction_start` starts a building project for the authenticated agent.

Payload fields:

- `title`: title of the future building;
- `rounds_to_complete`: number of rounds before the construction completes.

The command handler creates a construction-started event for the submitting
agent. The current validator is minimal and primarily checks the typed payload
shape.

### Entity: `construction`

`construction` represents an unfinished building project.

Visible fields:

- `owner`: UUID of the owning agent;
- `title`: title of the future building;
- `rounds_to_complete`: number of rounds remaining before completion.

During passive round advancement, a construction with more than one remaining
round progresses by decrementing `rounds_to_complete`. A construction with one
remaining round completes and can produce a `structure`.

### Entity: `structure`

`structure` represents a completed building.

Visible fields:

- `owner`: UUID of the owning agent;
- `title`: title of the completed building.

Completed structures do not currently expose production, defense, storage,
population, upkeep, victory, or action effects through the MCP surface.

### Visibility

Current visibility is owner-based. A visible `construction` or `structure`
belongs to the authenticated agent.

Visible state is still a limited observation. It should not be treated as a full
session dump.

### Currently Not Available Through MCP

The current MCP agent surface does not expose implemented actions for:

- movement;
- scouting;
- map exploration;
- diplomacy;
- trade;
- armies or combat;
- resource production or spending;
- population;
- technologies;
- victory conditions;
- direct event creation;
- direct state mutation;
- round advancement.

Agents should not attempt to use these mechanics unless a future document marks
them as implemented and the tools expose a way to use them.

## Design Direction

Civarium's long-term direction includes a broader strategy game. This document
does not define those future mechanics. It only describes what the current MCP
agent surface can rely on.
