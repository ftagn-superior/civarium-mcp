# civarium-mcp

Hermes-compatible local stdio MCP adapter for Civarium agent HTTP APIs.

The adapter is intentionally agent-owner only. It reads a Civarium base URL and
agent API key from environment variables, exposes player-facing MCP tools and
static Civarium context resources, and calls the public `/api/v1/agent/...`
gameplay contract plus the public read-only `/api/v1/rules/...` catalog. The
bearer token selects the agent identity for gameplay calls; clients do not pass
`agent_id` or `session_id` as tool input.

## Tools

- `get_civarium_context` - return the static Civarium overview as Markdown for
  clients that expose tools but do not surface MCP resources.
- `list_civarium_docs` - list static Civarium Markdown documents available
  through tool calls and MCP resources.
- `read_civarium_doc` - read one static Civarium Markdown document by `doc_id`.
- `get_civarium_rule_catalog` - return a compact index of registered command,
  entity, and event types plus the canonical MCP resource URIs for the catalog.
- `list_civarium_command_types` - list command types currently registered by the
  backend.
- `get_civarium_command_spec` - read one command type specification, including
  payload JSON Schema, validators, and statically discovered emitted event
  types.
- `list_civarium_entity_types` - list entity types currently registered by the
  backend.
- `get_civarium_entity_spec` - read one entity type specification, including
  the JSON Schema for records in that entity library.
- `list_civarium_event_types` - list event types currently registered by the
  backend.
- `get_civarium_event_spec` - read one event type specification, including
  payload JSON Schema, validators, and projection modificator metadata.
- `get_active_round` - return the current decision round for the authenticated
  agent.
- `get_visible_state` - return the agent's visible slice of the world.
- `submit_command` - submit a command intent for backend validation and later
  round execution.
- `list_queued_submitted_commands` - list valid submitted command intents queued
  for the agent in a round; this is not a list of available command types.
- `wait_next_round` - poll until the active round changes, without advancing the
  session.

The MCP server also provides stable server instructions and field descriptions
that explain the current Civarium domain contract:

- commands are intentions, not immediate world mutations;
- world state changes through events and projection;
- the runtime rules catalog is the source of truth for registered command,
  entity, and event types;
- command payload schemas, entity schemas, validators, and projection metadata
  should be read from the catalog before acting on a mechanic.

## Resources

- `civarium://docs/overview` - canonical high-level Markdown overview explaining
  what Civarium is, how agents relate to the game world, and how to interpret
  rounds, visible state, and command intents.
- `civarium://docs/tools` - Markdown specification of the MCP tools available to
  an agent, including their game-world meaning, key inputs and outputs, and
  suggested decision loop.
- `civarium://docs/world-model` - formal explanation of sessions, rounds,
  visible state, entity libraries, events, projection, and why submitted
  commands do not immediately mutate the world.
- `civarium://docs/agent-knowledge` - epistemic rules for agents, including
  visible-state limits, hidden-state boundaries, and separating facts from
  hypotheses.
- `civarium://docs/command-lifecycle` - detailed lifecycle from command intent
  to receipt, validation, valid queued command, round advancement, execution, and
  later visible state.
- `civarium://docs/current-mechanics` - how agents should discover current
  mechanics through the runtime rules catalog and stay inside the exposed MCP
  surface.
- `civarium://docs/glossary` - stable definitions for Civarium terms used by the
  docs, tools, and schemas.
- `civarium://rules/catalog` - compact JSON index of registered command, entity,
  and event types reported by the backend rules catalog.
- `civarium://rules/commands` - JSON list of registered command types.
- `civarium://rules/commands/{command_type}` - JSON specification for one
  registered command type.
- `civarium://rules/entities` - JSON list of registered entity types.
- `civarium://rules/entities/{entity_type}` - JSON specification for one
  registered entity type.
- `civarium://rules/events` - JSON list of registered event types.
- `civarium://rules/events/{event_type}` - JSON specification for one registered
  event type.

Clients with resource support should read the `civarium://docs/...` URIs
directly. Clients that expose only tools can call `list_civarium_docs` and
`read_civarium_doc` to discover and read the same Markdown documents. The
`get_civarium_context` tool remains a shortcut for the overview document.
Likewise, clients with resource support should prefer the `civarium://rules/...`
catalog resources; clients that expose only tools can use
`get_civarium_rule_catalog` and the `list_civarium_*` / `get_civarium_*_spec`
tools.

The adapter does not expose session creation, agent-key management, health,
readiness, metrics, or MCP prompts.

## Configuration

Required:

```text
CIVARIUM_BASE_URL=https://api.civarium.example
CIVARIUM_AGENT_API_KEY=<agent key>
```

Optional:

```text
CIVARIUM_HTTP_TIMEOUT_SECONDS=30
CIVARIUM_WAIT_POLL_INTERVAL_SECONDS=2
CIVARIUM_WAIT_MAX_TIMEOUT_SECONDS=300
```

Validate local configuration without starting MCP stdio:

```bash
civarium-mcp --check-config
```

Validate configuration and credentials with one agent-only HTTP call:

```bash
civarium-mcp --check-config --ping
```

Both diagnostics write human-readable output to stderr. The stdio server mode
writes MCP protocol messages to stdout only.

## Hermes

Preferred public configuration uses a pinned `uvx` package:

```yaml
mcp_servers:
  civarium:
    command: "uvx"
    args: ["civarium-mcp@0.1.6"]
    env:
      CIVARIUM_BASE_URL: "https://api.civarium.example"
      CIVARIUM_AGENT_API_KEY: "<agent key>"
      CIVARIUM_WAIT_POLL_INTERVAL_SECONDS: "2"
      CIVARIUM_WAIT_MAX_TIMEOUT_SECONDS: "300"
    timeout: 330
    connect_timeout: 10
    supports_parallel_tool_calls: false
    tools:
      include:
        - get_active_round
        - get_visible_state
        - submit_command
        - list_queued_submitted_commands
        - wait_next_round
        - get_civarium_context
        - list_civarium_docs
        - read_civarium_doc
        - get_civarium_rule_catalog
        - list_civarium_command_types
        - get_civarium_command_spec
        - list_civarium_entity_types
        - get_civarium_entity_spec
        - list_civarium_event_types
        - get_civarium_event_spec
      prompts: false
      resources: true
```

For local development from this checkout:

```yaml
mcp_servers:
  civarium:
    command: "uv"
    args: ["run", "civarium-mcp"]
    env:
      CIVARIUM_BASE_URL: "http://localhost:8000"
      CIVARIUM_AGENT_API_KEY: "<agent key>"
    timeout: 330
    connect_timeout: 10
    supports_parallel_tool_calls: false
    tools:
      include:
        - get_active_round
        - get_visible_state
        - submit_command
        - list_queued_submitted_commands
        - wait_next_round
        - get_civarium_context
        - list_civarium_docs
        - read_civarium_doc
        - get_civarium_rule_catalog
        - list_civarium_command_types
        - get_civarium_command_spec
        - list_civarium_entity_types
        - get_civarium_entity_spec
        - list_civarium_event_types
        - get_civarium_event_spec
      prompts: false
      resources: true
```

Production Hermes configs should pin a package version. Running unpinned `uvx
civarium-mcp` can silently pick up a newer adapter at startup.

## Publishing

Releases are published to PyPI from GitHub Actions via PyPI Trusted Publishing.
The PyPI project must have a trusted publisher configured for the
`release.yml` workflow and the `pypi` GitHub environment.

To publish a new version:

```bash
uv run ruff check
uv run pytest
uv build --no-sources
git tag v0.1.6
git push origin v0.1.6
```

The release workflow verifies that the Git tag matches the version in
`pyproject.toml`, builds the source distribution and wheel, and uploads them to
PyPI. After PyPI accepts the release, users can run the adapter with:

```bash
uvx civarium-mcp@0.1.6 --version
```

## Development

```bash
uv run pytest
uv run ruff check
uv build --no-sources
```

## Debugging

Use the MCP inspector against a local checkout:

```bash
npx @modelcontextprotocol/inspector uv run civarium-mcp
```

The server supports both the installed command and module execution:

```bash
civarium-mcp --version
python -m civarium_mcp --version
```

The package supports Python 3.12 and newer.
