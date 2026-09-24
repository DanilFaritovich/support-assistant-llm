from pathlib import Path

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
