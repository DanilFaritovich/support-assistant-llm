import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.department import DepartmentORM
from app.repositories.sqlalchemy_department_repository import (
    SqlAlchemyDepartmentRepository,
)
from app.schemas.department import Department


@pytest.mark.asyncio
class TestSqlAlchemyDepartmentRepository:
    async def test_get_all_with_existing_departments(
        self,
        session: AsyncSession,
        seeded_departments: list[DepartmentORM],
    ) -> None:
        """
        Verify that the repository retrieves all departments
        from the database and returns Pydantic schemas.
        """
        repository = SqlAlchemyDepartmentRepository(
            session=session,
        )

        result = await repository.get_all()

        assert len(result) == len(seeded_departments)

        assert all(isinstance(department, Department) for department in result)

        assert [
            (
                department.id,
                department.name,
                department.description,
            )
            for department in result
        ] == [
            (
                department.id,
                department.name,
                department.description,
            )
            for department in seeded_departments
        ]

    async def test_get_all_with_empty_database(
        self,
        session: AsyncSession,
    ) -> None:
        """
        Verify that the repository returns an empty list
        when the departments table contains no records.
        """
        repository = SqlAlchemyDepartmentRepository(
            session=session,
        )

        result = await repository.get_all()

        assert result == []

    async def test_get_by_id_with_existing_department(
        self,
        session: AsyncSession,
        seeded_departments: list[DepartmentORM],
    ) -> None:
        """
        Verify that the repository retrieves a department by ID
        and returns its Pydantic schema.
        """
        repository = SqlAlchemyDepartmentRepository(
            session=session,
        )
        expected_department = seeded_departments[0]

        result = await repository.get_by_id(
            department_id=expected_department.id,
        )

        assert result is not None
        assert isinstance(result, Department)

        assert result.id == expected_department.id
        assert result.name == expected_department.name
        assert result.description == expected_department.description

    async def test_get_by_id_with_nonexistent_department(
        self,
        session: AsyncSession,
        seeded_departments: list[DepartmentORM],
    ) -> None:
        """
        Verify that the repository returns None
        when the requested department does not exist.
        """
        repository = SqlAlchemyDepartmentRepository(
            session=session,
        )

        existing_ids = {department.id for department in seeded_departments}
        nonexistent_id = max(existing_ids, default=0) + 1

        result = await repository.get_by_id(
            department_id=nonexistent_id,
        )

        assert result is None

    async def test_get_by_id_with_empty_database(
        self,
        session: AsyncSession,
    ) -> None:
        """
        Verify that the repository returns None
        when the departments table is empty.
        """
        repository = SqlAlchemyDepartmentRepository(
            session=session,
        )

        result = await repository.get_by_id(
            department_id=1,
        )

        assert result is None
