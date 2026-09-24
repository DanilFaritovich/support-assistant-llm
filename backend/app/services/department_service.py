import logging

from app.ports.department_port import DepartmentRepository
from app.schemas.department import Department

logger = logging.getLogger(__name__)


class DepartmentService:
    """Provide access to available IT departments."""

    def __init__(
        self,
        department_repository: DepartmentRepository,
    ) -> None:
        self._department_repository = department_repository

    async def get_all(self) -> list[Department]:
        """Retrieve all available IT departments."""
        logger.debug("Loading available departments.")

        departments = await self._department_repository.get_all()

        logger.debug(
            "Loaded departments successfully: count=%d.",
            len(departments),
        )

        return departments

    async def get_by_id(
        self,
        department_id: int,
    ) -> Department | None:
        """Retrieve a department by ID using a direct repository lookup."""
        if department_id <= 0:
            raise ValueError("Department ID must be positive.")

        return await self._department_repository.get_by_id(department_id)
