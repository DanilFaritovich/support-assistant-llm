import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.department import DepartmentORM
from app.db.seed import load_demo_departments, seed_demo_departments


@pytest.mark.asyncio
async def test_demo_seed_is_idempotent(session: AsyncSession) -> None:
    expected_count = len(load_demo_departments())

    assert await seed_demo_departments(session) == expected_count
    assert await seed_demo_departments(session) == 0

    result = await session.execute(select(func.count()).select_from(DepartmentORM))
    assert result.scalar_one() == expected_count
