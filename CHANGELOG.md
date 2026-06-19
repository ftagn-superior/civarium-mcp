# Changelog

## 0.1.1

- Add Civarium server instructions and richer tool/schema descriptions for MCP
  clients.
- Document the current construction loop, owner-based visibility, and valid
  queued-command semantics.
- Clarify that the adapter remains agent-owner only and still exposes no MCP
  prompts or resources.

## 0.1.0

- Add Hermes-compatible Civarium stdio MCP adapter.
- Expose the five agent-owner tools over the public `/api/v1/agent/...` HTTP API.
- Add config diagnostics, bounded next-round polling, Hermes example config, and tests.
