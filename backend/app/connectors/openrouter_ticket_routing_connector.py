import json
import logging
from collections.abc import Sequence

from pydantic import ValidationError

from app.connectors.openrouter_base_connector import (
    LLMResponseError,
    OpenRouterBaseConnector,
)
from app.ports.ticket_routing_port import TicketRoutingPort
from app.prompts.ticket_routing import SYSTEM_PROMPT
from app.schemas.department import Department
from app.schemas.ticket_routing import TicketRoutingResult

logger = logging.getLogger(__name__)


class TicketRoutingError(Exception):
    """Raised when a ticket routing result is invalid."""


class OpenRouterTicketRoutingConnector(
    OpenRouterBaseConnector,
    TicketRoutingPort,
):
    async def route(
        self,
        ticket_text: str,
        departments: Sequence[Department],
    ) -> TicketRoutingResult:
        """Generate a ticket title and select its department."""
        if not ticket_text.strip():
            logger.warning("Ticket routing rejected: ticket text is empty.")
            raise ValueError("Ticket text must not be empty.")

        if not departments:
            logger.warning("Ticket routing rejected: department list is empty.")
            raise ValueError("Department list must not be empty.")

        department_ids = {department.id for department in departments}

        if len(department_ids) != len(departments):
            logger.warning("Ticket routing rejected: duplicate department IDs.")
            raise ValueError("Department IDs must be unique.")

        logger.debug(
            "Preparing ticket routing request.",
            extra={"departments_count": len(departments)},
        )

        departments_json = json.dumps(
            [department.model_dump(mode="json") for department in departments],
            ensure_ascii=False,
        )

        user_prompt = (
            "Available IT departments:\n"
            f"{departments_json}\n\n"
            "Original bug report:\n"
            f"{ticket_text}"
        )

        try:
            content = await self._complete(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                response_schema=TicketRoutingResult.model_json_schema(),
                schema_name="ticket_routing",
            )
        except LLMResponseError as exc:
            # The base connector has already logged the response failure.
            raise TicketRoutingError(str(exc)) from exc

        logger.debug("Validating ticket routing response.")

        try:
            result = TicketRoutingResult.model_validate_json(content)
        except ValidationError as exc:
            logger.warning(
                "Ticket routing response validation failed: "
                "response does not match the expected schema."
            )
            raise TicketRoutingError(
                "The LLM response does not match the expected ticket routing schema."
            ) from exc

        if not result.title.strip():
            logger.warning(
                "Ticket routing response validation failed: generated title is empty."
            )
            raise TicketRoutingError("The generated ticket title must not be empty.")

        if not result.reasoning.strip():
            logger.warning(
                "Ticket routing response validation failed: "
                "department selection reasoning is empty."
            )
            raise TicketRoutingError(
                "The department selection reasoning must not be empty."
            )

        if result.department_id not in department_ids:
            logger.warning(
                "Ticket routing response validation failed: "
                "selected department is not available."
            )
            raise TicketRoutingError("The selected department is not available.")

        logger.info(
            "Ticket routing completed successfully.",
            extra={
                "event": "llm_ticket_routing_completed",
                "department_id": result.department_id,
            },
        )

        return result
