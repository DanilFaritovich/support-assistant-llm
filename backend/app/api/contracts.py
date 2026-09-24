from typing import Protocol

from app.schemas.department import Department
from app.schemas.ticket_draft import TicketDraft
from app.schemas.ticket_routing import TicketRoutingResult


class DepartmentReader(Protocol):
    """Provide access to available departments."""

    async def get_all(self) -> list[Department]:
        """Return all available departments."""
        ...


class TicketRouter(Protocol):
    """Route a single support ticket using available departments."""

    async def route(
        self,
        ticket_text: str,
        departments: list[Department],
    ) -> TicketRoutingResult:
        """Return the generated title and department selection."""
        ...


class TicketProcessor(Protocol):
    """Generate a ticket description for a selected department."""

    async def process(
        self,
        ticket_text: str,
        department_id: int,
        template: str,
    ) -> TicketDraft:
        """Return the generated ticket description."""
        ...
