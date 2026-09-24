from unittest.mock import AsyncMock, MagicMock

import pytest

from app.connectors.openrouter_ticket_drafting_connector import (
    TicketDraftingError,
)
from app.ports.ticket_drafting_port import TicketDraftingPort
from app.schemas.department import Department
from app.schemas.ticket_draft import TicketDraft
from app.services.ticket_drafting_service import TicketDraftingService

BUG_REPORT = "При отправке POST-запроса на /api/auth/login сервер возвращает HTTP 500."

DESCRIPTION_TEMPLATE = "Issue:\nSteps to reproduce:\nActual result:\nExpected result:"


class TestTicketDraftingService:
    @pytest.fixture
    def dependencies(
        self,
    ) -> tuple[TicketDraftingService, MagicMock, TicketDraft]:
        """Create a drafting service with a mocked drafting port."""
        drafting_port = MagicMock(spec=TicketDraftingPort)

        expected_result = TicketDraft(description="Generated bug report description.")

        drafting_port.draft = AsyncMock(return_value=expected_result)

        service = TicketDraftingService(
            ticket_drafting=drafting_port,
        )

        return service, drafting_port, expected_result

    @pytest.mark.asyncio
    async def test_draft_returns_generated_description(
        self,
        dependencies: tuple[
            TicketDraftingService,
            MagicMock,
            TicketDraft,
        ],
        list_departments: list[Department],
    ) -> None:
        """Pass one ticket to the drafting port and return its result."""
        service, drafting_port, expected_result = dependencies
        department = list_departments[0]

        result = await service.draft(
            ticket_text=BUG_REPORT,
            department=department,
            template=DESCRIPTION_TEMPLATE,
        )

        assert result is expected_result
        assert isinstance(result, TicketDraft)
        assert result.description == "Generated bug report description."

        drafting_port.draft.assert_awaited_once_with(
            ticket_text=BUG_REPORT,
            department=department,
            template=DESCRIPTION_TEMPLATE,
        )

    @pytest.mark.asyncio
    async def test_draft_rejects_empty_ticket(
        self,
        dependencies: tuple[
            TicketDraftingService,
            MagicMock,
            TicketDraft,
        ],
        list_departments: list[Department],
    ) -> None:
        """Reject an empty ticket before calling the drafting port."""
        service, drafting_port, _ = dependencies

        with pytest.raises(
            ValueError,
            match="Ticket text must not be empty",
        ):
            await service.draft(
                ticket_text="   ",
                department=list_departments[0],
                template=DESCRIPTION_TEMPLATE,
            )

        drafting_port.draft.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_draft_rejects_empty_template(
        self,
        dependencies: tuple[
            TicketDraftingService,
            MagicMock,
            TicketDraft,
        ],
        list_departments: list[Department],
    ) -> None:
        """Reject an empty template before calling the drafting port."""
        service, drafting_port, _ = dependencies

        with pytest.raises(
            ValueError,
            match="Description template must not be empty",
        ):
            await service.draft(
                ticket_text=BUG_REPORT,
                department=list_departments[0],
                template="   ",
            )

        drafting_port.draft.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_draft_propagates_connector_error(
        self,
        dependencies: tuple[
            TicketDraftingService,
            MagicMock,
            TicketDraft,
        ],
        list_departments: list[Department],
    ) -> None:
        """Propagate a drafting failure without returning a false success."""
        service, drafting_port, _ = dependencies
        department = list_departments[0]

        drafting_port.draft.side_effect = TicketDraftingError("Invalid LLM response.")

        with pytest.raises(
            TicketDraftingError,
            match="Invalid LLM response",
        ):
            await service.draft(
                ticket_text=BUG_REPORT,
                department=department,
                template=DESCRIPTION_TEMPLATE,
            )

        drafting_port.draft.assert_awaited_once_with(
            ticket_text=BUG_REPORT,
            department=department,
            template=DESCRIPTION_TEMPLATE,
        )
