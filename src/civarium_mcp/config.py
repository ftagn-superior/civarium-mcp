"""Environment-backed adapter configuration."""

from __future__ import annotations

from pydantic import AliasChoices, Field, SecretStr, ValidationError, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AdapterConfig(BaseSettings):
    """Configuration required by the local Civarium MCP adapter."""

    base_url: str = Field(validation_alias=AliasChoices("CIVARIUM_BASE_URL", "base_url"))
    agent_api_key: SecretStr = Field(
        validation_alias=AliasChoices("CIVARIUM_AGENT_API_KEY", "agent_api_key"),
    )
    http_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        validation_alias=AliasChoices("CIVARIUM_HTTP_TIMEOUT_SECONDS", "http_timeout_seconds"),
    )
    wait_poll_interval_seconds: float = Field(
        default=2.0,
        gt=0,
        validation_alias=AliasChoices(
            "CIVARIUM_WAIT_POLL_INTERVAL_SECONDS",
            "wait_poll_interval_seconds",
        ),
    )
    wait_max_timeout_seconds: float = Field(
        default=300.0,
        gt=0,
        validation_alias=AliasChoices(
            "CIVARIUM_WAIT_MAX_TIMEOUT_SECONDS",
            "wait_max_timeout_seconds",
        ),
    )

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    @field_validator("base_url")
    @classmethod
    def normalize_base_url(cls, value: str) -> str:
        """Normalize a player-supplied Civarium API root URL."""
        import httpx

        stripped = value.strip()
        if not stripped:
            raise ValueError("CIVARIUM_BASE_URL must not be blank")

        url = httpx.URL(stripped)
        if url.scheme not in {"http", "https"} or not url.host:
            raise ValueError("CIVARIUM_BASE_URL must be an absolute http(s) URL")

        return str(url).rstrip("/")

    @field_validator("agent_api_key")
    @classmethod
    def validate_agent_api_key(cls, value: SecretStr) -> SecretStr:
        """Reject blank bearer tokens without exposing the token value."""
        if not value.get_secret_value().strip():
            raise ValueError("CIVARIUM_AGENT_API_KEY must not be blank")
        return value


def format_config_error(exc: ValidationError) -> str:
    """Return a concise, secret-safe validation error string."""
    errors: list[str] = []
    for error in exc.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in error["loc"])
        errors.append(f"{location}: {error['msg']}")
    return "; ".join(errors)
