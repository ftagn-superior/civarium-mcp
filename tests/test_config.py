from __future__ import annotations

from pydantic import ValidationError

from civarium_mcp.__main__ import main
from civarium_mcp.config import AdapterConfig, format_config_error


def test_config_loads_env_and_normalizes_base_url(monkeypatch) -> None:
    monkeypatch.setenv("CIVARIUM_BASE_URL", "https://api.civarium.example/")
    monkeypatch.setenv("CIVARIUM_AGENT_API_KEY", "agent-secret")
    monkeypatch.setenv("CIVARIUM_HTTP_TIMEOUT_SECONDS", "12.5")

    config = AdapterConfig()

    assert config.base_url == "https://api.civarium.example"
    assert config.agent_api_key.get_secret_value() == "agent-secret"
    assert config.http_timeout_seconds == 12.5


def test_config_error_is_secret_safe(monkeypatch) -> None:
    monkeypatch.setenv("CIVARIUM_BASE_URL", "not-a-url")
    monkeypatch.setenv("CIVARIUM_AGENT_API_KEY", "super-secret-token")

    try:
        AdapterConfig()
    except ValidationError as exc:
        message = format_config_error(exc)
    else:  # pragma: no cover
        raise AssertionError("expected invalid config")

    assert "CIVARIUM_BASE_URL" in message
    assert "super-secret-token" not in message


def test_check_config_does_not_ping_backend(monkeypatch, capsys) -> None:
    monkeypatch.setenv("CIVARIUM_BASE_URL", "https://api.civarium.example")
    monkeypatch.setenv("CIVARIUM_AGENT_API_KEY", "agent-secret")

    exit_code = main(["--check-config"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == ""
    assert "configuration OK" in captured.err


def test_version_prints_to_stdout(capsys) -> None:
    exit_code = main(["--version"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.startswith("civarium-mcp ")
