"""HTTP gateway over Civarium's agent-only API contract."""

from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID

import httpx
from pydantic import ValidationError

from civarium_mcp.config import AdapterConfig
from civarium_mcp.schemas import (
    AcceptedCommandListOutput,
    AgentRoundOutput,
    CommandReceivedOutput,
    VisibleStateOutput,
)

_ROUND_COMMANDS_PATH_RE = re.compile(
    r"^agent/rounds/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}/commands$",
)
_ALLOWED_STATIC_ENDPOINTS = {
    ("GET", "agent/round"),
    ("GET", "agent/state"),
    ("POST", "agent/commands"),
}


class CivariumApiError(RuntimeError):
    """Secret-safe error raised for Civarium HTTP and contract failures."""

    def __init__(self, *, path: str, message: str, status_code: int | None = None) -> None:
        self.path = path
        self.message = message
        self.status_code = status_code
        super().__init__(self._format())

    def _format(self) -> str:
        if self.status_code is None:
            return f"Civarium API request failed for {self.path}: {self.message}"
        return f"Civarium API returned HTTP {self.status_code} for {self.path}: {self.message}"


class HttpCivariumGateway:
    """Thin async client for the public `/api/v1/agent/...` endpoints."""

    def __init__(
        self,
        config: AdapterConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._config = config
        self._transport = transport

    @property
    def api_base_url(self) -> str:
        """Return the normalized `/api/v1/` base URL used by httpx."""
        return f"{self._config.base_url}/api/v1/"

    async def get_active_round(self) -> AgentRoundOutput:
        """Call `GET /api/v1/agent/round`."""
        data = await self._request("GET", "agent/round")
        return self._validate_output(AgentRoundOutput, data, "agent/round")

    async def get_visible_state(self) -> VisibleStateOutput:
        """Call `GET /api/v1/agent/state`."""
        data = await self._request("GET", "agent/state")
        return self._validate_output(VisibleStateOutput, data, "agent/state")

    async def submit_command(
        self,
        *,
        round_id: UUID,
        client_command_id: UUID,
        command_type: str,
        payload: dict[str, Any],
    ) -> CommandReceivedOutput:
        """Call `POST /api/v1/agent/commands`."""
        data = await self._request(
            "POST",
            "agent/commands",
            json_body={
                "round_id": str(round_id),
                "client_command_id": str(client_command_id),
                "command_type": command_type,
                "payload": payload,
            },
        )
        return self._validate_output(CommandReceivedOutput, data, "agent/commands")

    async def list_my_commands(self, round_id: UUID) -> AcceptedCommandListOutput:
        """Call `GET /api/v1/agent/rounds/{round_id}/commands`."""
        path = f"agent/rounds/{round_id}/commands"
        data = await self._request("GET", path)
        return self._validate_output(AcceptedCommandListOutput, data, path)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._ensure_allowed_endpoint(method, path)
        token = self._config.agent_api_key.get_secret_value()

        try:
            async with httpx.AsyncClient(
                base_url=self.api_base_url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=self._config.http_timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.request(method, path, json=json_body)
        except httpx.HTTPError as exc:
            raise CivariumApiError(
                path=path,
                message=f"transport error: {type(exc).__name__}",
            ) from exc

        if response.status_code >= 400:
            raise CivariumApiError(
                path=path,
                status_code=response.status_code,
                message=self._safe_response_message(response, token),
            )

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise CivariumApiError(
                path=path,
                status_code=response.status_code,
                message="response was not valid JSON",
            ) from exc

        if not isinstance(payload, dict):
            raise CivariumApiError(
                path=path,
                status_code=response.status_code,
                message="response JSON was not an object",
            )
        return payload

    def _ensure_allowed_endpoint(self, method: str, path: str) -> None:
        endpoint = (method.upper(), path)
        if endpoint in _ALLOWED_STATIC_ENDPOINTS:
            return
        if method.upper() == "GET" and _ROUND_COMMANDS_PATH_RE.match(path):
            return
        raise CivariumApiError(path=path, message="endpoint is not allowed by adapter policy")

    def _safe_response_message(self, response: httpx.Response, token: str) -> str:
        message = response.reason_phrase or "request failed"
        try:
            payload = response.json()
        except json.JSONDecodeError:
            payload = None

        if isinstance(payload, dict):
            detail = payload.get("detail") or payload.get("message") or payload.get("error")
            if isinstance(detail, str):
                message = detail
            elif detail is not None:
                message = json.dumps(detail, ensure_ascii=True, sort_keys=True)

        return self._redact(message, token)[:400]

    @staticmethod
    def _redact(message: str, secret: str) -> str:
        return message.replace(secret, "[redacted]") if secret else message

    @staticmethod
    def _validate_output(model: type[Any], data: dict[str, Any], path: str) -> Any:
        try:
            return model.model_validate(data)
        except ValidationError as exc:
            raise CivariumApiError(
                path=path,
                message="response shape did not match the expected Civarium agent API",
            ) from exc
