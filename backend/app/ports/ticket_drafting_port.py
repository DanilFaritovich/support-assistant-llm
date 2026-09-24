from typing import Protocol

from app.schemas.department import Department
from app.schemas.ticket_draft import TicketDraft


class TicketDraftingPort(Protocol):
    async def draft(
        self,
        ticket_text: str,
        department: Department,
        template: str,
    ) -> TicketDraft:
        """
        Generate a structured ticket description
        based on the provided template.

        Args:
            ticket_text: The original ticket content.
            department: The selected IT department.
            template: The required ticket description template.

        Returns:
            The generated ticket description.
        """
        ...
