import json
import logging
from pathlib import Path

from pydantic import BaseModel, TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.department import DepartmentORM

logger = logging.getLogger(__name__)

DEPARTMENTS_PATH = (
    Path(__file__).resolve().parents[2] / "resources" / "departments.json"
)


class DemoDepartment(BaseModel):
    """Validated department seed record."""

    name: str
    description: str


def load_demo_departments() -> list[DemoDepartment]:
    """Load validated, repository-owned demo departments."""
    data = json.loads(DEPARTMENTS_PATH.read_text(encoding="utf-8"))
    departments = TypeAdapter(list[DemoDepartment]).validate_python(data)

    if not departments:
        raise ValueError("Demo department configuration must not be empty.")

    normalized_names = [item.name.strip().casefold() for item in departments]
    if len(normalized_names) != len(set(normalized_names)):
        raise ValueError("Demo department names must be unique.")

    return departments


async def seed_demo_departments(session: AsyncSession) -> int:
    """Insert missing demo departments without changing existing records."""
    departments = load_demo_departments()
    result = await session.execute(select(DepartmentORM.name))
    existing_names = {name.casefold() for name in result.scalars()}
    missing = [
        DepartmentORM(name=item.name, description=item.description)
        for item in departments
        if item.name.casefold() not in existing_names
    ]

    if missing:
        session.add_all(missing)
        await session.commit()
        logger.info("Seeded demo IT departments: count=%d.", len(missing))

    return len(missing)
