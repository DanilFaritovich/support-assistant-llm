import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.ports.llm_quota_port import LLMQuotaPort
from app.schemas.department import Department

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEPARTMENTS_JSON_PATH = PROJECT_ROOT / "resources" / "departments.json"


@pytest.fixture
def list_departments() -> list[Department]:
    """Load department schemas from the project JSON file."""
    with DEPARTMENTS_JSON_PATH.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        departments_data = json.load(file)

    return [
        Department(
            id=index,
            name=item["name"],
            description=item.get("description"),
        )
        for index, item in enumerate(departments_data, start=1)
    ]


@pytest.fixture
def llm_quota() -> MagicMock:
    """Provide an allowed shared-quota operation for service tests."""
    quota = MagicMock(spec=LLMQuotaPort)
    quota.consume = AsyncMock()
    return quota
