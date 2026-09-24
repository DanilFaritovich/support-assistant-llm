import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_defaults_to_automatic_free_model_router() -> None:
    settings = Settings(_env_file=None)

    assert settings.openrouter_model_list == ["openrouter/free"]


def test_accepts_only_free_models_in_fallback_order() -> None:
    settings = Settings(
        _env_file=None,
        openrouter_models="vendor/a:free, vendor/b:free",
    )

    assert settings.openrouter_model_list == ["vendor/a:free", "vendor/b:free"]


def test_rejects_paid_models() -> None:
    with pytest.raises(ValidationError, match="accepts only"):
        Settings(_env_file=None, openrouter_models="vendor/paid-model")
