from __future__ import annotations

import json

import httpx
import pytest
from support import AGENT_ID, CLIENT_COMMAND_ID, COMMAND_ID, ROUND_ID, SESSION_ID

from civarium_mcp.config import AdapterConfig
from civarium_mcp.gateway import CivariumApiError, HttpCivariumGateway


@pytest.mark.parametrize(
    "base_url,expected_url",
    [
        ("https://api.civarium.example", "https://api.civarium.example/api/v1/agent/round"),
        ("https://api.civarium.example/", "https://api.civarium.example/api/v1/agent/round"),
    ],
)
async def test_get_active_round_joins_base_url_and_sends_bearer_auth(
    base_url: str,
    expected_url: str,
) -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "agent_id": str(AGENT_ID),
                "session_id": str(SESSION_ID),
                "round_id": str(ROUND_ID),
                "round_idx": 3,
            },
        )

    config = AdapterConfig(base_url=base_url, agent_api_key="agent-secret")
    gateway = HttpCivariumGateway(config, transport=httpx.MockTransport(handler))

    active_round = await gateway.get_active_round()

    assert str(requests[0].url) == expected_url
    assert requests[0].headers["Authorization"] == "Bearer agent-secret"
    assert active_round.session_id == SESSION_ID
    assert active_round.round_id == ROUND_ID
    assert not hasattr(active_round, "agent_id")


async def test_submit_command_forwards_body_without_identity_fields(adapter_config) -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        body = json.loads(request.content)
        assert body == {
            "round_id": str(ROUND_ID),
            "client_command_id": str(CLIENT_COMMAND_ID),
            "command_type": "construction_start",
            "payload": {"title": "Granary", "rounds_to_complete": 2},
        }
        assert "agent_id" not in body
        assert "session_id" not in body
        return httpx.Response(
            200,
            json={
                "command_id": str(COMMAND_ID),
                "round_id": str(ROUND_ID),
                "client_command_id": str(CLIENT_COMMAND_ID),
                "is_valid": False,
                "checks": {"enough_resources": "failed"},
            },
        )

    gateway = HttpCivariumGateway(adapter_config, transport=httpx.MockTransport(handler))

    receipt = await gateway.submit_command(
        round_id=ROUND_ID,
        client_command_id=CLIENT_COMMAND_ID,
        command_type="construction_start",
        payload={"title": "Granary", "rounds_to_complete": 2},
    )

    assert str(requests[0].url).endswith("/api/v1/agent/commands")
    assert receipt.is_valid is False
    assert receipt.checks == {"enough_resources": "failed"}


async def test_list_queued_submitted_commands_omits_backend_agent_id(
    adapter_config,
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "agent_id": str(AGENT_ID),
                "round_id": str(ROUND_ID),
                "commands": [
                    {
                        "command_id": str(COMMAND_ID),
                        "client_command_id": str(CLIENT_COMMAND_ID),
                        "command_type": "construction_start",
                        "payload": {"title": "Granary"},
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ],
            },
        )

    gateway = HttpCivariumGateway(adapter_config, transport=httpx.MockTransport(handler))

    result = await gateway.list_queued_submitted_commands(ROUND_ID)

    assert result.round_id == ROUND_ID
    assert not hasattr(result, "agent_id")
    assert result.commands[0].command_type == "construction_start"


async def test_rules_catalog_endpoints_are_allowed_and_validated(adapter_config) -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if path.endswith("/api/v1/rules/commands"):
            return httpx.Response(200, json={"command_types": ["construction_start"]})
        if path.endswith("/api/v1/rules/commands/construction_start"):
            return httpx.Response(
                200,
                json={
                    "command_type": "construction_start",
                    "description": "Payload for starting construction.",
                    "payload_schema": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "rounds_to_complete": {"type": "integer"},
                        },
                    },
                    "events": ["construction_started"],
                    "validators": [
                        {
                            "name": "check_construction_start",
                            "description": "Validate construction start.",
                        }
                    ],
                },
            )
        if path.endswith("/api/v1/rules/entities"):
            return httpx.Response(200, json={"entity_types": ["construction", "structure"]})
        if path.endswith("/api/v1/rules/entities/structure"):
            return httpx.Response(
                200,
                json={
                    "entity_type": "structure",
                    "description": "Completed building.",
                    "entity_schema": {
                        "type": "object",
                        "properties": {"title": {"type": "string"}},
                    },
                },
            )
        if path.endswith("/api/v1/rules/events"):
            return httpx.Response(200, json={"event_types": ["construction_started"]})
        if path.endswith("/api/v1/rules/events/construction_started"):
            return httpx.Response(
                200,
                json={
                    "event_type": "construction_started",
                    "description": "Construction started.",
                    "payload_schema": {
                        "type": "object",
                        "properties": {"title": {"type": "string"}},
                    },
                    "validators": [{"name": "check_construction_started"}],
                    "modificator": {"name": "on_construction_started"},
                },
            )
        return httpx.Response(404, json={"detail": "unexpected path"})

    gateway = HttpCivariumGateway(adapter_config, transport=httpx.MockTransport(handler))

    command_types = await gateway.list_command_types()
    command_spec = await gateway.get_command_spec("construction_start")
    entity_types = await gateway.list_entity_types()
    entity_spec = await gateway.get_entity_spec("structure")
    event_types = await gateway.list_event_types()
    event_spec = await gateway.get_event_spec("construction_started")

    assert [str(request.url) for request in requests] == [
        "https://api.civarium.example/api/v1/rules/commands",
        "https://api.civarium.example/api/v1/rules/commands/construction_start",
        "https://api.civarium.example/api/v1/rules/entities",
        "https://api.civarium.example/api/v1/rules/entities/structure",
        "https://api.civarium.example/api/v1/rules/events",
        "https://api.civarium.example/api/v1/rules/events/construction_started",
    ]
    assert all(request.headers["Authorization"] == "Bearer agent-secret" for request in requests)
    assert command_types.command_types == ["construction_start"]
    assert command_spec.events == ["construction_started"]
    assert entity_types.entity_types == ["construction", "structure"]
    assert entity_spec.entity_type == "structure"
    assert event_types.event_types == ["construction_started"]
    assert event_spec.modificator.name == "on_construction_started"


async def test_gateway_errors_are_secret_safe(adapter_config) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"detail": "bad key agent-secret"})

    gateway = HttpCivariumGateway(adapter_config, transport=httpx.MockTransport(handler))

    with pytest.raises(CivariumApiError) as exc_info:
        await gateway.get_active_round()

    message = str(exc_info.value)
    assert "agent-secret" not in message
    assert "[redacted]" in message


async def test_gateway_rejects_non_agent_endpoint(adapter_config) -> None:
    gateway = HttpCivariumGateway(adapter_config, transport=httpx.MockTransport(lambda _: None))

    with pytest.raises(CivariumApiError):
        await gateway._request("GET", "health")
