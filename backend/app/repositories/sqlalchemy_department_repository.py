import logging

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.department import DepartmentORM
from app.ports.department_port import DepartmentRepository
from app.schemas.department import Department

logger = logging.getLogger(__name__)


class SqlAlchemyDepartmentRepository(DepartmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_all(self) -> list[Department]:
        """
        Retrieve all available IT departments from the database.

        Returns:
            A list of department schemas.

        Raises:
            SQLAlchemyError:
                If a database operation fails.
        """
        logger.debug("Fetching all IT departments from the database")

        try:
            statement = select(DepartmentORM).order_by(DepartmentORM.id)

            result = await self._session.execute(statement)

            departments = result.scalars().all()

            logger.debug(
                "Retrieved %d IT departments from the database",
                len(departments),
            )

            if not departments:
                logger.warning("No IT departments found in the database")

            return [
                Department(
                    id=department.id,
                    name=department.name,
                    description=department.description,
                )
                for department in departments
            ]

        except SQLAlchemyError:
            logger.exception("Failed to retrieve IT departments from the database")
            raise

    async def get_by_id(self, department_id: int) -> Department | None:
        """Retrieve a department by its primary key."""
        logger.debug(
            "Loading department: department_id=%d.",
            department_id,
        )

        try:
            department = await self._session.get(
                DepartmentORM,
                department_id,
            )
        except SQLAlchemyError:
            logger.exception(
                "Failed to load department: department_id=%d.",
                department_id,
            )
            raise

        if department is None:
            logger.debug(
                "Department not found: department_id=%d.",
                department_id,
            )
            return None

        return Department(
            id=department.id,
            name=department.name,
            description=department.description,
        )
