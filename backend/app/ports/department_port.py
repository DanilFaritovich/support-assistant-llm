from typing import Protocol

from app.schemas.department import Department


class DepartmentRepository(Protocol):
    async def get_all(self) -> list[Department]:
        """
        Retrieve all available IT departments.

        Returns:
            A list of available IT departments.
        """
        ...

    async def get_by_id(self, department_id: int) -> Department | None:
        """Return a department by ID, or None if it does not exist."""
        ...
