import logging

from app.exceptions import DepartmentNotFoundError
from app.ports.llm_quota_port import LLMQuotaPort
from app.schemas.ticket_draft import TicketDraft
from app.services.department_service import DepartmentService
from app.services.ticket_drafting_service import TicketDraftingService

logger = logging.getLogger(__name__)


class TicketProcessingService:
    """Generate a description for a ticket with a selected department."""

    def __init__(
        self,
        department_service: DepartmentService,
        ticket_drafting_service: TicketDraftingService,
        llm_quota: LLMQuotaPort,
    ) -> None:
        self._department_service = department_service
        self._ticket_drafting_service = ticket_drafting_service
        self._llm_quota = llm_quota

    async def process(
        self,
        ticket_text: str,
        department_id: int,
        template: str,
        client_id: str,
    ) -> TicketDraft:
        """
        Generate a ticket description using a previously selected department.

        Args:
            ticket_text: The original support ticket.
            department_id: ID of the department selected during routing.
            template: The description template selected by the user.
            client_id: Transport-derived quota identity.

        Returns:
            A generated ticket description.

        Raises:
            ValueError: If the ticket, department ID, or template is invalid.
            DepartmentNotFoundError: If the selected department does not exist.
        """
        if not ticket_text.strip():
            logger.warning("Ticket processing rejected: ticket text is empty.")
            raise ValueError("Ticket text must not be empty.")

        if department_id <= 0:
            logger.warning("Ticket processing rejected: department ID is invalid.")
            raise ValueError("Department ID must be positive.")

        if not template.strip():
            logger.warning("Ticket processing rejected: description template is empty.")
            raise ValueError("Description template must not be empty.")

        logger.debug(
            "Starting ticket description generation.",
            extra={"department_id": department_id},
        )

        department = await self._department_service.get_by_id(
            department_id,
        )

        if department is None:
            logger.warning("Ticket processing rejected: department not found.")
            raise DepartmentNotFoundError("The selected department does not exist.")

        await self._llm_quota.consume(client_id)

        result = await self._ticket_drafting_service.draft(
            ticket_text=ticket_text,
            department=department,
            template=template,
        )

        logger.info(
            "Ticket description generated successfully.",
            extra={
                "event": "ticket_description_generated",
                "department_id": department_id,
            },
        )

        return result
