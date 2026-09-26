import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_defaults_to_automatic_free_model_router() -> None:
    settings = Settings(_env_file=None)

    assert settings.openrouter_model_list == ["openrouter/free"]
    assert settings.llm_rate_limit_per_minute == 10
    assert settings.llm_rate_limit_per_day == 20


def test_accepts_only_free_models_in_fallback_order() -> None:
    settings = Settings(
        _env_file=None,
        openrouter_models="vendor/a:free, vendor/b:free",
    )

    assert settings.openrouter_model_list == ["vendor/a:free", "vendor/b:free"]


def test_rejects_paid_models() -> None:
    with pytest.raises(ValidationError, match="accepts only"):
        Settings(_env_file=None, openrouter_models="vendor/paid-model")


def test_accepts_configurable_llm_rate_limits() -> None:
    settings = Settings(
        _env_file=None,
        llm_rate_limit_per_minute=3,
        llm_rate_limit_per_day=7,
    )

    assert settings.llm_rate_limit_per_minute == 3
    assert settings.llm_rate_limit_per_day == 7


@pytest.mark.parametrize(
    ("setting_name", "value"),
    [
        ("llm_rate_limit_per_minute", 0),
        ("llm_rate_limit_per_day", 0),
    ],
)
def test_rejects_non_positive_llm_rate_limits(
    setting_name: str,
    value: int,
) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{setting_name: value})
