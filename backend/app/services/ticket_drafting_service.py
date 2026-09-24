import logging

from app.ports.ticket_drafting_port import TicketDraftingPort
from app.schemas.department import Department
from app.schemas.ticket_draft import TicketDraft

logger = logging.getLogger(__name__)


class TicketDraftingService:
    """Generate a structured description for a single support ticket."""

    def __init__(
        self,
        ticket_drafting: TicketDraftingPort,
    ) -> None:
        self._ticket_drafting = ticket_drafting

    async def draft(
        self,
        ticket_text: str,
        department: Department,
        template: str,
    ) -> TicketDraft:
        """
        Generate a ticket description using the selected department
        and the provided description template.

        Args:
            ticket_text: The original ticket content.
            department: The department selected for the ticket.
            template: The required ticket description template.

        Returns:
            The generated ticket description.

        Raises:
            ValueError: If the ticket text or template is empty.
        """
        if not ticket_text.strip():
            logger.warning("Ticket drafting rejected: ticket text is empty.")
            raise ValueError("Ticket text must not be empty.")

        if not template.strip():
            logger.warning("Ticket drafting rejected: description template is empty.")
            raise ValueError("Description template must not be empty.")

        logger.debug(
            "Starting ticket drafting: department_id=%d.",
            department.id,
        )

        result = await self._ticket_drafting.draft(
            ticket_text=ticket_text,
            department=department,
            template=template,
        )

        logger.info(
            "Ticket drafting completed successfully: department_id=%d.",
            department.id,
        )

        return result
