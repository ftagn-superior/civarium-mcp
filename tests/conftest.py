from __future__ import annotations

import pytest

from civarium_mcp.config import AdapterConfig


@pytest.fixture
def adapter_config() -> AdapterConfig:
    return AdapterConfig(
        base_url="https://api.civarium.example/",
        agent_api_key="agent-secret",
        http_timeout_seconds=1.0,
        wait_poll_interval_seconds=0.001,
        wait_max_timeout_seconds=0.02,
    )
