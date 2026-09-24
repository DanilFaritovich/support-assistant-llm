import json
import logging

from pydantic import ValidationError

from app.connectors.openrouter_base_connector import (
    LLMResponseError,
    OpenRouterBaseConnector,
)
from app.ports.ticket_drafting_port import TicketDraftingPort
from app.prompts.ticket_drafting import SYSTEM_PROMPT
from app.schemas.department import Department
from app.schemas.ticket_draft import TicketDraft

logger = logging.getLogger(__name__)


class TicketDraftingError(Exception):
    """Raised when the LLM returns an invalid ticket draft."""


class OpenRouterTicketDraftingConnector(
    OpenRouterBaseConnector,
    TicketDraftingPort,
):
    """Generate a bug report description using an LLM."""

    async def draft(
        self,
        ticket_text: str,
        department: Department,
        template: str,
    ) -> TicketDraft:
        """
        Generate a structured description for a single bug report.

        Args:
            ticket_text: The original bug report.
            department: The department selected for the ticket.
            template: The required bug report description template.

        Returns:
            The generated ticket description.

        Raises:
            ValueError: If the ticket text or template is empty.
            TicketDraftingError: If the LLM returns an invalid result.
            openai.APIError: If the LLM API request fails.
        """
        if not ticket_text.strip():
            logger.warning("Ticket drafting rejected: ticket text is empty.")
            raise ValueError("Ticket text must not be empty.")

        if not template.strip():
            logger.warning("Ticket drafting rejected: description template is empty.")
            raise ValueError("Description template must not be empty.")

        logger.debug(
            "Preparing ticket drafting request: department_id=%d.",
            department.id,
        )

        request_data = {
            "department": department.model_dump(mode="json"),
            "template": template,
            "original_ticket": ticket_text,
        }

        user_prompt = (
            "Generate a description for the following single bug report.\n"
            "Use the provided department and description template.\n\n"
            "Input data:\n"
            f"{json.dumps(request_data, ensure_ascii=False)}"
        )

        try:
            content = await self._complete(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_schema=TicketDraft.model_json_schema(),
                schema_name="ticket_draft",
            )
        except LLMResponseError as exc:
            # The base connector has already logged the response failure.
            raise TicketDraftingError(str(exc)) from exc

        logger.debug("Validating ticket drafting response.")

        try:
            result = TicketDraft.model_validate_json(content)
        except ValidationError as exc:
            logger.warning(
                "Ticket drafting response validation failed: "
                "response does not match the expected schema."
            )
            raise TicketDraftingError(
                "The LLM response does not match the expected ticket drafting schema."
            ) from exc

        if not result.description.strip():
            logger.warning(
                "Ticket drafting response validation failed: "
                "generated description is empty."
            )
            raise TicketDraftingError(
                "The generated ticket description must not be empty."
            )

        logger.debug(
            "Ticket drafting completed successfully: department_id=%d.",
            department.id,
        )

        return result
