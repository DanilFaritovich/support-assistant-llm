from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"

DATABASE_PATH = DATA_DIR / "app.db"

DEFAULT_DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH.as_posix()}"


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    """

    database_url: str = Field(
        default=DEFAULT_DATABASE_URL,
        description="Database connection URL.",
    )

    openrouter_api_key: SecretStr | None = Field(
        default=None,
        description="OpenRouter API key used only by the backend.",
    )

    openrouter_models: str = Field(
        default="openrouter/free",
        description="Comma-separated free OpenRouter model IDs in fallback order.",
    )

    openrouter_timeout_seconds: float = Field(
        default=60.0,
        gt=0,
        le=180,
        description="Timeout for a single OpenRouter request.",
    )

    openrouter_max_retries: int = Field(
        default=2,
        ge=0,
        le=3,
        description="Maximum number of SDK retries for transient failures.",
    )

    openrouter_site_url: str | None = Field(
        default=None,
        description="Optional public project URL sent in the HTTP-Referer header.",
    )

    llm_rate_limit_per_minute: int = Field(
        default=10,
        ge=1,
        description="Maximum LLM operations per client IP in 60 seconds.",
    )

    llm_rate_limit_per_day: int = Field(
        default=20,
        ge=1,
        description="Maximum LLM operations per client IP in 24 hours.",
    )

    redis_url: SecretStr = Field(
        default=SecretStr("redis://localhost:6379/0"),
        description="Redis URL for shared LLM quota state.",
    )

    log_level: str = Field(
        default="INFO",
        description="Application logging level.",
    )

    log_format: Literal["json", "text"] = Field(
        default="json",
        description="Application log output format.",
    )

    service_name: str = Field(
        default="support-assistant-backend",
        min_length=1,
        description="Service name attached to structured logs.",
    )

    environment: str = Field(
        default="development",
        min_length=1,
        description="Deployment environment attached to structured logs.",
    )

    @field_validator("openrouter_models")
    @classmethod
    def validate_free_models(cls, value: str) -> str:
        """Reject empty lists and paid model identifiers."""
        models = [model.strip() for model in value.split(",") if model.strip()]

        if not models:
            raise ValueError("OPENROUTER_MODELS must contain at least one model.")

        invalid = [
            model
            for model in models
            if model != "openrouter/free" and not model.endswith(":free")
        ]
        if invalid:
            raise ValueError(
                "OPENROUTER_MODELS accepts only openrouter/free or :free models."
            )

        return ",".join(models)

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Normalize and validate the configured Python log level."""
        normalized = value.upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in allowed:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(sorted(allowed))}.")
        return normalized

    @property
    def openrouter_model_list(self) -> list[str]:
        """Return validated OpenRouter model IDs in fallback order."""
        return self.openrouter_models.split(",")

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
