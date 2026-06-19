"""Static MCP resources for Civarium reference context."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files

from mcp.server.fastmcp import FastMCP


@dataclass(frozen=True)
class CivariumDocReference:
    """Static Civarium document metadata shared by resources and tool fallbacks."""

    doc_id: str
    uri: str
    name: str
    title: str
    mime_type: str
    filename: str
    description: str


CIVARIUM_DOCS: tuple[CivariumDocReference, ...] = (
    CivariumDocReference(
        doc_id="overview",
        uri="civarium://docs/overview",
        name="civarium_overview",
        title="Civarium Overview",
        mime_type="text/markdown",
        filename="civarium-overview.md",
        description=(
            "Read this first when you need the high-level Civarium premise, agent role, "
            "rounds, visible state, and command intent semantics."
        ),
    ),
    CivariumDocReference(
        doc_id="tools",
        uri="civarium://docs/tools",
        name="civarium_tools",
        title="Civarium Agent Tools",
        mime_type="text/markdown",
        filename="civarium-tools.md",
        description=(
            "Read this when you need the available MCP tools, their inputs and outputs, "
            "and the recommended decision loop for playing through Hermes or another "
            "client."
        ),
    ),
    CivariumDocReference(
        doc_id="world-model",
        uri="civarium://docs/world-model",
        name="civarium_world_model",
        title="Civarium World Model",
        mime_type="text/markdown",
        filename="civarium-world-model.md",
        description=(
            "Read this when you need to understand sessions, active rounds, visible "
            "versus hidden state, entity libraries, events, projection, and why submit "
            "does not mutate state."
        ),
    ),
    CivariumDocReference(
        doc_id="agent-knowledge",
        uri="civarium://docs/agent-knowledge",
        name="civarium_agent_knowledge",
        title="Civarium Agent Knowledge",
        mime_type="text/markdown",
        filename="civarium-agent-knowledge.md",
        description=(
            "Read this when you need the agent's knowledge boundaries: what counts as "
            "observed fact, what stays hidden, and how to keep hypotheses separate from "
            "backend facts."
        ),
    ),
    CivariumDocReference(
        doc_id="command-lifecycle",
        uri="civarium://docs/command-lifecycle",
        name="civarium_command_lifecycle",
        title="Civarium Command Lifecycle",
        mime_type="text/markdown",
        filename="civarium-command-lifecycle.md",
        description=(
            "Read this when you need to reason about command drafts, submit_command "
            "receipts, validation checks, queued commands, round advancement, "
            "execution, and later visible state."
        ),
    ),
    CivariumDocReference(
        doc_id="current-mechanics",
        uri="civarium://docs/current-mechanics",
        name="civarium_current_mechanics",
        title="Civarium Current Mechanics",
        mime_type="text/markdown",
        filename="civarium-current-mechanics.md",
        description=(
            "Read this when you need the current implemented mechanics: "
            "construction_start, construction, structure, owner-based visibility, and "
            "mechanics not available through MCP."
        ),
    ),
    CivariumDocReference(
        doc_id="glossary",
        uri="civarium://docs/glossary",
        name="civarium_glossary",
        title="Civarium Glossary",
        mime_type="text/markdown",
        filename="civarium-glossary.md",
        description=(
            "Read this when you need stable definitions for Civarium terms such as "
            "agent, session, round, visible state, command intent, receipt, event, and "
            "projection."
        ),
    ),
)
CIVARIUM_DOCS_BY_ID = {doc.doc_id: doc for doc in CIVARIUM_DOCS}

OVERVIEW_DOC = CIVARIUM_DOCS_BY_ID["overview"]
TOOLS_DOC = CIVARIUM_DOCS_BY_ID["tools"]
OVERVIEW_RESOURCE_URI = OVERVIEW_DOC.uri
OVERVIEW_RESOURCE_NAME = OVERVIEW_DOC.name
OVERVIEW_RESOURCE_TITLE = OVERVIEW_DOC.title
OVERVIEW_MIME_TYPE = OVERVIEW_DOC.mime_type
TOOLS_RESOURCE_URI = TOOLS_DOC.uri
TOOLS_RESOURCE_NAME = TOOLS_DOC.name
TOOLS_RESOURCE_TITLE = TOOLS_DOC.title
TOOLS_MIME_TYPE = TOOLS_DOC.mime_type


def list_civarium_docs() -> tuple[CivariumDocReference, ...]:
    """Return metadata for packaged Civarium reference documents."""
    return CIVARIUM_DOCS


def get_civarium_doc(doc_id: str) -> CivariumDocReference:
    """Return metadata for one packaged Civarium reference document."""
    try:
        return CIVARIUM_DOCS_BY_ID[doc_id]
    except KeyError as exc:
        valid_doc_ids = ", ".join(sorted(CIVARIUM_DOCS_BY_ID))
        raise ValueError(
            f"unknown Civarium doc_id {doc_id!r}; expected one of {valid_doc_ids}"
        ) from exc


def load_civarium_doc(doc_id: str) -> str:
    """Return the Markdown content for one packaged Civarium document."""
    doc = get_civarium_doc(doc_id)
    return files("civarium_mcp.docs").joinpath(doc.filename).read_text(encoding="utf-8")


def load_civarium_overview() -> str:
    """Return the canonical static overview for Civarium agents."""
    return load_civarium_doc("overview")


def load_civarium_tools() -> str:
    """Return the canonical static tool specification for Civarium agents."""
    return load_civarium_doc("tools")


def register_resources(server: FastMCP) -> None:
    """Register static Civarium reference documents as MCP resources."""

    def make_reader(doc_id: str):
        def read_civarium_doc_resource() -> str:
            return load_civarium_doc(doc_id)

        return read_civarium_doc_resource

    for doc in CIVARIUM_DOCS:
        server.resource(
            doc.uri,
            name=doc.name,
            title=doc.title,
            description=doc.description,
            mime_type=doc.mime_type,
        )(make_reader(doc.doc_id))
