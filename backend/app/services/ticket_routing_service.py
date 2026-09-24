import logging

from app.ports.ticket_routing_port import TicketRoutingPort
from app.schemas.department import Department
from app.schemas.ticket_routing import TicketRoutingResult

logger = logging.getLogger(__name__)


class TicketRoutingService:
    """Generate a ticket title and select the responsible department."""

    def __init__(
        self,
        ticket_routing: TicketRoutingPort,
    ) -> None:
        self._ticket_routing = ticket_routing

    async def route(
        self,
        ticket_text: str,
        departments: list[Department],
    ) -> TicketRoutingResult:
        """
        Route a single bug report using the provided departments.

        Args:
            ticket_text: The original bug report.
            departments: Available IT departments.

        Returns:
            The generated title, selected department ID,
            and reasoning behind the selection.

        Raises:
            ValueError: If the ticket text or department list is empty.
        """
        if not ticket_text.strip():
            logger.warning("Ticket routing rejected: ticket text is empty.")
            raise ValueError("Ticket text must not be empty.")

        if not departments:
            logger.warning("Ticket routing rejected: department list is empty.")
            raise ValueError("Department list must not be empty.")

        logger.debug(
            "Starting ticket routing: departments_count=%d.",
            len(departments),
        )

        result = await self._ticket_routing.route(
            ticket_text=ticket_text,
            departments=departments,
        )

        logger.info(
            "Ticket routing completed successfully: department_id=%d.",
            result.department_id,
        )

        return result
