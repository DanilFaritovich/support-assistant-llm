from collections.abc import Sequence
from typing import Protocol

from app.schemas.department import Department
from app.schemas.ticket_routing import TicketRoutingResult


class TicketRoutingPort(Protocol):
    async def route(
        self,
        ticket_text: str,
        departments: Sequence[Department],
    ) -> TicketRoutingResult:
        """
        Generate a ticket title and determine the responsible
        IT department based on the ticket content.

        Args:
            ticket_text: The original ticket content.
            departments: Available IT departments.

        Returns:
            The generated title, selected department ID,
            and an explanation of the department selection.
        """
        ...
