# Changelog

## 0.1.4

- Add five static Civarium agent docs: world model, agent knowledge, command
  lifecycle, current mechanics, and glossary.
- Expose the new docs both as MCP resources and through `list_civarium_docs` /
  `read_civarium_doc`.
- Make static doc descriptions more routing-friendly for clients choosing which
  document to read next.

## 0.1.3

- Add `list_civarium_docs` and `read_civarium_doc` read-only tools so clients
  that do not expose MCP resource-reading operations can still discover and read
  the packaged Civarium Markdown docs through normal tool calls.
- Keep `get_civarium_context` as a backward-compatible overview shortcut.

## 0.1.2

- Add a packaged Civarium overview Markdown document exposed as
  `civarium://docs/overview`.
- Add a packaged Civarium tool specification document exposed as
  `civarium://docs/tools`.
- Add `get_civarium_context` as a read-only fallback tool for MCP clients that do
  not surface resources or server instructions to the model.
- Enable resources in the Hermes example config and document the new context
  contract.

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
