import pytest
from pydantic import ValidationError

from app.schemas.workspace import WorkspaceData


def settings_data() -> dict:
    return {
        "departments": [{"id": 1, "name": "IT"}],
        "examples": [],
        "templates": [{"id": "template", "name": "Default", "text": "Summary:"}],
        "default_template_id": "template",
    }


@pytest.mark.parametrize(
    "change",
    [
        {"departments": []},
        {"departments": [{"id": 1, "name": "IT"}, {"id": 1, "name": "Other"}]},
        {"departments": [{"id": 1, "name": "IT"}, {"id": 2, "name": " it "}]},
        {"departments": [{"id": 1, "name": "   "}]},
        {"templates": []},
        {"templates": [{"id": "a", "name": "A", "text": " "}]},
        {"default_template_id": "missing"},
        {"format_version": 2},
        {"examples": [{"id": "a", "name": "A", "text": "x" * 4001}]},
        {"templates": [{"id": "template", "name": "A", "text": "x" * 2001}]},
        {"examples": [{"id": "a", "name": "A", "text": "Text"}] * 21},
    ],
)
def test_rejects_invalid_workspace_settings(change: dict) -> None:
    with pytest.raises(ValidationError):
        WorkspaceData.model_validate(settings_data() | change)


def test_total_storage_limit_counts_utf8_bytes() -> None:
    data = settings_data()
    data["examples"] = [
        {"id": str(i), "name": "Example", "text": "я" * 2500} for i in range(3)
    ]
    with pytest.raises(ValidationError, match="15,000"):
        WorkspaceData.model_validate(data)


def test_accepts_valid_custom_settings_and_optional_language() -> None:
    result = WorkspaceData.model_validate(settings_data())
    assert result.default_template_id == "template"
    assert result.templates[0].locale is None
