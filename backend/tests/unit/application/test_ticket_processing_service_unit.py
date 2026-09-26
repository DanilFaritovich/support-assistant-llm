from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.exceptions import DepartmentNotFoundError, LLMQuotaExceededError
from app.schemas.department import Department
from app.schemas.ticket_draft import TicketDraft
from app.services.department_service import DepartmentService
from app.services.ticket_drafting_service import TicketDraftingService
from app.services.ticket_processing_service import TicketProcessingService

BUG_REPORT = "При отправке POST-запроса на /api/auth/login сервер возвращает HTTP 500."

DESCRIPTION_TEMPLATE = "Issue:\nActual result:\nExpected result:"

EXPECTED_DESCRIPTION = (
    "Issue:\n"
    "Пользователь не может авторизоваться.\n\n"
    "Actual result:\n"
    "Сервер возвращает HTTP 500.\n\n"
    "Expected result:\n"
    "Не указано."
)


@dataclass
class Dependencies:
    """Hold mocked dependencies and expected test data."""

    service: TicketProcessingService
    department_service: MagicMock
    drafting_service: MagicMock
    llm_quota: MagicMock
    selected_department: Department
    draft_result: TicketDraft


class TestTicketProcessingService:
    @pytest.fixture
    def dependencies(self, llm_quota: MagicMock) -> Dependencies:
        """Create the application service with mocked dependencies."""
        selected_department = Department(
            id=2,
            name="Test Backend Department",
            description="Responsible for server-side APIs.",
        )

        draft_result = TicketDraft(
            description=EXPECTED_DESCRIPTION,
        )

        department_service = MagicMock(spec=DepartmentService)
        department_service.get_by_id = AsyncMock(
            return_value=selected_department,
        )

        drafting_service = MagicMock(spec=TicketDraftingService)
        drafting_service.draft = AsyncMock(
            return_value=draft_result,
        )

        service = TicketProcessingService(
            department_service=department_service,
            ticket_drafting_service=drafting_service,
            llm_quota=llm_quota,
        )

        return Dependencies(
            service=service,
            department_service=department_service,
            drafting_service=drafting_service,
            llm_quota=llm_quota,
            selected_department=selected_department,
            draft_result=draft_result,
        )

    @pytest.mark.asyncio
    async def test_process_returns_generated_description(
        self,
        dependencies: Dependencies,
    ) -> None:
        """Generate a description using the previously selected department."""
        result = await dependencies.service.process(
            ticket_text=BUG_REPORT,
            department_id=dependencies.selected_department.id,
            template=DESCRIPTION_TEMPLATE,
            client_id="192.0.2.1",
        )

        assert isinstance(result, TicketDraft)
        assert result == dependencies.draft_result
        assert result.description == EXPECTED_DESCRIPTION
        dependencies.llm_quota.consume.assert_awaited_once_with("192.0.2.1")

        dependencies.department_service.get_by_id.assert_awaited_once_with(
            dependencies.selected_department.id,
        )

        dependencies.drafting_service.draft.assert_awaited_once_with(
            ticket_text=BUG_REPORT,
            department=dependencies.selected_department,
            template=DESCRIPTION_TEMPLATE,
        )

    @pytest.mark.asyncio
    async def test_process_stops_before_drafting_when_quota_is_exhausted(
        self,
        dependencies: Dependencies,
    ) -> None:
        dependencies.llm_quota.consume.side_effect = LLMQuotaExceededError(
            retry_after=60
        )

        with pytest.raises(LLMQuotaExceededError):
            await dependencies.service.process(
                ticket_text=BUG_REPORT,
                department_id=dependencies.selected_department.id,
                template=DESCRIPTION_TEMPLATE,
                client_id="192.0.2.1",
            )

        dependencies.department_service.get_by_id.assert_awaited_once()
        dependencies.drafting_service.draft.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_process_rejects_empty_ticket(
        self,
        dependencies: Dependencies,
    ) -> None:
        """Reject an empty ticket before calling dependent services."""
        with pytest.raises(
            ValueError,
            match="Ticket text must not be empty",
        ):
            await dependencies.service.process(
                ticket_text="   ",
                department_id=dependencies.selected_department.id,
                template=DESCRIPTION_TEMPLATE,
                client_id="192.0.2.1",
            )

        dependencies.department_service.get_by_id.assert_not_awaited()
        dependencies.drafting_service.draft.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_process_rejects_empty_template(
        self,
        dependencies: Dependencies,
    ) -> None:
        """Reject an empty template before calling dependent services."""
        with pytest.raises(
            ValueError,
            match="Description template must not be empty",
        ):
            await dependencies.service.process(
                ticket_text=BUG_REPORT,
                department_id=dependencies.selected_department.id,
                template="   ",
                client_id="192.0.2.1",
            )

        dependencies.department_service.get_by_id.assert_not_awaited()
        dependencies.drafting_service.draft.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("department_id", [0, -1])
    async def test_process_rejects_invalid_department_id(
        self,
        dependencies: Dependencies,
        department_id: int,
    ) -> None:
        """Reject department IDs that are not positive."""
        with pytest.raises(
            ValueError,
            match="Department ID must be positive",
        ):
            await dependencies.service.process(
                ticket_text=BUG_REPORT,
                department_id=department_id,
                template=DESCRIPTION_TEMPLATE,
                client_id="192.0.2.1",
            )

        dependencies.department_service.get_by_id.assert_not_awaited()
        dependencies.drafting_service.draft.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_process_rejects_unknown_department(
        self,
        dependencies: Dependencies,
    ) -> None:
        """Reject a department ID that does not exist in the database."""
        dependencies.department_service.get_by_id.return_value = None

        with pytest.raises(
            DepartmentNotFoundError,
            match="The selected department does not exist",
        ):
            await dependencies.service.process(
                ticket_text=BUG_REPORT,
                department_id=999,
                template=DESCRIPTION_TEMPLATE,
                client_id="192.0.2.1",
            )

        dependencies.department_service.get_by_id.assert_awaited_once_with(
            999,
        )
        dependencies.drafting_service.draft.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_process_propagates_department_service_error(
        self,
        dependencies: Dependencies,
    ) -> None:
        """Propagate a department lookup failure without generating a draft."""
        dependencies.department_service.get_by_id.side_effect = RuntimeError(
            "Department loading failed."
        )

        with pytest.raises(
            RuntimeError,
            match="Department loading failed",
        ):
            await dependencies.service.process(
                ticket_text=BUG_REPORT,
                department_id=dependencies.selected_department.id,
                template=DESCRIPTION_TEMPLATE,
                client_id="192.0.2.1",
            )

        dependencies.department_service.get_by_id.assert_awaited_once_with(
            dependencies.selected_department.id,
        )
        dependencies.drafting_service.draft.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_process_propagates_drafting_service_error(
        self,
        dependencies: Dependencies,
    ) -> None:
        """Propagate a drafting failure after loading the selected department."""
        dependencies.drafting_service.draft.side_effect = RuntimeError(
            "Ticket drafting failed."
        )

        with pytest.raises(
            RuntimeError,
            match="Ticket drafting failed",
        ):
            await dependencies.service.process(
                ticket_text=BUG_REPORT,
                department_id=dependencies.selected_department.id,
                template=DESCRIPTION_TEMPLATE,
                client_id="192.0.2.1",
            )

        dependencies.department_service.get_by_id.assert_awaited_once_with(
            dependencies.selected_department.id,
        )

        dependencies.drafting_service.draft.assert_awaited_once_with(
            ticket_text=BUG_REPORT,
            department=dependencies.selected_department,
            template=DESCRIPTION_TEMPLATE,
        )
