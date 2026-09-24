from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.db.models.department import DepartmentORM
from app.schemas.department import Department


@pytest_asyncio.fixture
async def session(
    tmp_path: Path,
) -> AsyncIterator[AsyncSession]:
    """Create an isolated SQLite database and session for each test."""
    database_path = tmp_path / "test.db"

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path}",
    )

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(
            bind=engine,
            expire_on_commit=False,
        )

        async with session_factory() as db_session:
            yield db_session

    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def seeded_departments(
    session: AsyncSession,
    list_departments: list[Department],
) -> list[DepartmentORM]:
    """Persist departments provided by the shared test fixture."""
    departments = [
        DepartmentORM(
            id=department.id,
            name=department.name,
            description=department.description,
        )
        for department in list_departments
    ]

    session.add_all(departments)
    await session.commit()

    return departments
