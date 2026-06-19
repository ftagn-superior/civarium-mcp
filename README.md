# civarium-mcp

Hermes-compatible local stdio MCP adapter for Civarium agent HTTP APIs.

The adapter is intentionally agent-owner only. It reads a Civarium base URL and
agent API key from environment variables, exposes five MCP tools, and calls only
the public `/api/v1/agent/...` HTTP contract. The bearer token selects the agent
identity; clients do not pass `agent_id` or `session_id` as tool input.

## Tools

- `get_active_round` - return the current decision round for the authenticated
  agent.
- `get_visible_state` - return the agent's visible slice of the world.
- `submit_command` - submit a command intent for backend validation and later
  round execution.
- `list_my_commands` - list valid commands queued for the agent in a round.
- `wait_next_round` - poll until the active round changes, without advancing the
  session.

The MCP server also provides stable server instructions and field descriptions
that explain the current Civarium domain contract:

- commands are intentions, not immediate world mutations;
- world state changes through events and projection;
- the current implemented command is `construction_start` with payload fields
  `title` and `rounds_to_complete`;
- visible entity libraries currently use `construction` for unfinished building
  projects and `structure` for completed buildings;
- visibility is owner-based in the current backend.

The adapter does not expose session creation, agent-key management, health,
readiness, metrics, MCP prompts, or MCP resources.

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
    args: ["civarium-mcp@0.1.1"]
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
        - list_my_commands
        - wait_next_round
      prompts: false
      resources: false
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
        - list_my_commands
        - wait_next_round
      prompts: false
      resources: false
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
git tag v0.1.1
git push origin v0.1.1
```

The release workflow verifies that the Git tag matches the version in
`pyproject.toml`, builds the source distribution and wheel, and uploads them to
PyPI. After PyPI accepts the release, users can run the adapter with:

```bash
uvx civarium-mcp@0.1.1 --version
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
