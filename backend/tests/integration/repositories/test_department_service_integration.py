import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.department import DepartmentORM
from app.repositories.sqlalchemy_department_repository import (
    SqlAlchemyDepartmentRepository,
)
from app.schemas.department import Department
from app.services.department_service import DepartmentService


class TestDepartmentServiceIntegration:
    @pytest.mark.asyncio
    async def test_get_all_returns_departments_from_database(
        self,
        session: AsyncSession,
        seeded_departments: list[DepartmentORM],
        list_departments: list[Department],
    ) -> None:
        """Retrieve all departments through the service and repository."""
        repository = SqlAlchemyDepartmentRepository(session)
        service = DepartmentService(
            department_repository=repository,
        )

        result = await service.get_all()

        assert result == list_departments
        assert len(result) == len(seeded_departments)
        assert all(isinstance(item, Department) for item in result)

    @pytest.mark.asyncio
    async def test_get_by_id_returns_existing_department(
        self,
        session: AsyncSession,
        seeded_departments: list[DepartmentORM],
    ) -> None:
        """Retrieve an existing department by ID through the service."""
        repository = SqlAlchemyDepartmentRepository(session)
        service = DepartmentService(
            department_repository=repository,
        )
        expected_department = seeded_departments[0]

        result = await service.get_by_id(
            department_id=expected_department.id,
        )

        assert result is not None
        assert isinstance(result, Department)
        assert result.id == expected_department.id
        assert result.name == expected_department.name
        assert result.description == expected_department.description

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_for_nonexistent_department(
        self,
        session: AsyncSession,
        seeded_departments: list[DepartmentORM],
    ) -> None:
        """Return None when the requested department does not exist."""
        repository = SqlAlchemyDepartmentRepository(session)
        service = DepartmentService(
            department_repository=repository,
        )

        nonexistent_id = max(department.id for department in seeded_departments) + 1

        result = await service.get_by_id(
            department_id=nonexistent_id,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_id_rejects_invalid_department_id(
        self,
        session: AsyncSession,
    ) -> None:
        """Reject department IDs that are not positive."""
        repository = SqlAlchemyDepartmentRepository(session)
        service = DepartmentService(
            department_repository=repository,
        )

        with pytest.raises(
            ValueError,
            match="Department ID must be positive",
        ):
            await service.get_by_id(department_id=0)

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_with_empty_database(
        self,
        session: AsyncSession,
    ) -> None:
        """Return None when the departments table is empty."""
        repository = SqlAlchemyDepartmentRepository(session)
        service = DepartmentService(
            department_repository=repository,
        )

        result = await service.get_by_id(department_id=1)

        assert result is None
