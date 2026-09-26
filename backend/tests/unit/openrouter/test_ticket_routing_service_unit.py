from unittest.mock import AsyncMock, MagicMock

import pytest

from app.connectors.openrouter_ticket_routing_connector import TicketRoutingError
from app.exceptions import LLMQuotaExceededError
from app.ports.ticket_routing_port import TicketRoutingPort
from app.schemas.department import Department
from app.schemas.ticket_routing import TicketRoutingResult
from app.services.ticket_routing_service import TicketRoutingService

BUG_REPORT = "При отправке POST-запроса на /api/auth/login сервер возвращает HTTP 500."


class TestTicketRoutingService:
    @pytest.fixture
    def dependencies(
        self,
        list_departments: list[Department],
        llm_quota: MagicMock,
    ) -> tuple[
        TicketRoutingService,
        MagicMock,
        TicketRoutingResult,
    ]:
        """Create a routing service with a mocked routing port."""
        routing_port = MagicMock(spec=TicketRoutingPort)

        expected_result = TicketRoutingResult(
            title="Ошибка авторизации: HTTP 500",
            department_id=list_departments[0].id,
            reasoning="The selected department handles the reported issue.",
        )

        routing_port.route = AsyncMock(return_value=expected_result)

        service = TicketRoutingService(
            ticket_routing=routing_port,
            llm_quota=llm_quota,
        )

        return service, routing_port, expected_result

    @pytest.mark.asyncio
    async def test_route_returns_routing_result(
        self,
        dependencies: tuple[
            TicketRoutingService,
            MagicMock,
            TicketRoutingResult,
        ],
        list_departments: list[Department],
        llm_quota: MagicMock,
    ) -> None:
        """Pass one bug and available departments to the routing port."""
        service, routing_port, expected_result = dependencies

        result = await service.route(
            ticket_text=BUG_REPORT,
            departments=list_departments,
            client_id="192.0.2.1",
        )

        assert result is expected_result
        llm_quota.consume.assert_awaited_once_with("192.0.2.1")

        routing_port.route.assert_awaited_once_with(
            ticket_text=BUG_REPORT,
            departments=list_departments,
        )

    @pytest.mark.asyncio
    async def test_route_stops_before_connector_when_quota_is_exhausted(
        self,
        dependencies: tuple[
            TicketRoutingService,
            MagicMock,
            TicketRoutingResult,
        ],
        list_departments: list[Department],
        llm_quota: MagicMock,
    ) -> None:
        service, routing_port, _ = dependencies
        llm_quota.consume.side_effect = LLMQuotaExceededError(retry_after=60)

        with pytest.raises(LLMQuotaExceededError):
            await service.route(
                ticket_text=BUG_REPORT,
                departments=list_departments,
                client_id="192.0.2.1",
            )

        routing_port.route.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_route_rejects_empty_ticket(
        self,
        dependencies: tuple[
            TicketRoutingService,
            MagicMock,
            TicketRoutingResult,
        ],
        list_departments: list[Department],
    ) -> None:
        """Reject an empty ticket before calling the routing port."""
        service, routing_port, _ = dependencies

        with pytest.raises(
            ValueError,
            match="Ticket text must not be empty",
        ):
            await service.route(
                ticket_text="   ",
                departments=list_departments,
                client_id="192.0.2.1",
            )

        routing_port.route.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_route_rejects_empty_departments(
        self,
        dependencies: tuple[
            TicketRoutingService,
            MagicMock,
            TicketRoutingResult,
        ],
    ) -> None:
        """Reject an empty department list before calling the routing port."""
        service, routing_port, _ = dependencies

        with pytest.raises(
            ValueError,
            match="Department list must not be empty",
        ):
            await service.route(
                ticket_text=BUG_REPORT,
                departments=[],
                client_id="192.0.2.1",
            )

        routing_port.route.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_route_propagates_connector_error(
        self,
        dependencies: tuple[
            TicketRoutingService,
            MagicMock,
            TicketRoutingResult,
        ],
        list_departments: list[Department],
    ) -> None:
        """Propagate a routing failure without hiding the error."""
        service, routing_port, _ = dependencies

        routing_port.route.side_effect = TicketRoutingError("Invalid LLM response")

        with pytest.raises(
            TicketRoutingError,
            match="Invalid LLM response",
        ):
            await service.route(
                ticket_text=BUG_REPORT,
                departments=list_departments,
                client_id="192.0.2.1",
            )

        routing_port.route.assert_awaited_once_with(
            ticket_text=BUG_REPORT,
            departments=list_departments,
        )
