import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.connectors.openrouter_ticket_routing_connector import (
    OpenRouterTicketRoutingConnector,
    TicketRoutingError,
)
from app.schemas.department import Department
from app.schemas.ticket_routing import TicketRoutingResult

BUG_REPORT = "При отправке POST-запроса на /api/auth/login сервер возвращает HTTP 500."


class TestOpenRouterTicketRoutingConnector:
    @staticmethod
    def make_completion(
        content: str | None,
        finish_reason: str = "stop",
    ) -> SimpleNamespace:
        """Build a mocked Chat Completion response."""
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=content),
                    finish_reason=finish_reason,
                )
            ]
        )

    @pytest.mark.asyncio
    async def test_route_parses_valid_json(
        self,
        routing_connector: OpenRouterTicketRoutingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Parse a valid LLM response into the routing schema."""
        selected_department = list_departments[0]

        response_content = json.dumps(
            {
                "title": "Ошибка авторизации: HTTP 500",
                "department_id": selected_department.id,
                "reasoning": ("The selected department handles this issue."),
            },
            ensure_ascii=False,
        )

        llm_client.chat.completions.create.return_value = self.make_completion(
            response_content
        )

        result = await routing_connector.route(
            ticket_text=BUG_REPORT,
            departments=list_departments,
        )

        assert isinstance(result, TicketRoutingResult)
        assert result.title == "Ошибка авторизации: HTTP 500"
        assert result.department_id == selected_department.id
        assert result.reasoning == ("The selected department handles this issue.")

        llm_client.chat.completions.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_route_sends_one_bug_and_all_departments(
        self,
        routing_connector: OpenRouterTicketRoutingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Send one bug report and the complete department list."""
        selected_department = list_departments[0]

        response_content = json.dumps(
            {
                "title": "Ошибка авторизации",
                "department_id": selected_department.id,
                "reasoning": "The selected department handles this issue.",
            },
            ensure_ascii=False,
        )

        llm_client.chat.completions.create.return_value = self.make_completion(
            response_content
        )

        await routing_connector.route(
            ticket_text=BUG_REPORT,
            departments=list_departments,
        )

        llm_client.chat.completions.create.assert_awaited_once()

        request = llm_client.chat.completions.create.await_args.kwargs

        assert request["model"] == "test-model:free"
        assert request["temperature"] == 0.0
        assert request["extra_body"] == {
            "models": ["fallback-model:free"],
            "provider": {"require_parameters": True},
        }
        assert request["response_format"]["type"] == "json_schema"
        assert request["response_format"]["json_schema"]["strict"] is True

        messages = request["messages"]

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

        user_content = messages[1]["content"]

        departments_json, ticket_text = user_content.split(
            "\n\nOriginal bug report:\n",
            maxsplit=1,
        )

        assert ticket_text == BUG_REPORT
        assert departments_json.startswith("Available IT departments:\n")

        departments_json = departments_json.removeprefix("Available IT departments:\n")

        assert json.loads(departments_json) == [
            department.model_dump(mode="json") for department in list_departments
        ]

    @pytest.mark.asyncio
    async def test_route_rejects_invalid_json(
        self,
        routing_connector: OpenRouterTicketRoutingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Reject an LLM response that is not valid JSON."""
        llm_client.chat.completions.create.return_value = self.make_completion(
            "This is not JSON."
        )

        with pytest.raises(
            TicketRoutingError,
            match="does not match",
        ):
            await routing_connector.route(
                ticket_text=BUG_REPORT,
                departments=list_departments,
            )

    @pytest.mark.asyncio
    async def test_route_rejects_missing_required_field(
        self,
        routing_connector: OpenRouterTicketRoutingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Reject a JSON response without required routing fields."""
        response_content = json.dumps(
            {
                "title": "Пользователь не может авторизоваться",
            },
            ensure_ascii=False,
        )

        llm_client.chat.completions.create.return_value = self.make_completion(
            response_content
        )

        with pytest.raises(
            TicketRoutingError,
            match="does not match",
        ):
            await routing_connector.route(
                ticket_text=BUG_REPORT,
                departments=list_departments,
            )

    @pytest.mark.asyncio
    async def test_route_rejects_unexpected_fields(
        self,
        routing_connector: OpenRouterTicketRoutingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        response_content = json.dumps(
            {
                "title": "Title",
                "department_id": list_departments[0].id,
                "reasoning": "Reason",
                "internal_note": "must not be accepted",
            }
        )
        llm_client.chat.completions.create.return_value = self.make_completion(
            response_content
        )

        with pytest.raises(TicketRoutingError, match="does not match"):
            await routing_connector.route(BUG_REPORT, list_departments)

    @pytest.mark.asyncio
    async def test_route_rejects_unknown_department(
        self,
        routing_connector: OpenRouterTicketRoutingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Reject a department ID that is not in the provided list."""
        unknown_department_id = (
            max(department.id for department in list_departments) + 1
        )

        response_content = json.dumps(
            {
                "title": "Ошибка авторизации",
                "department_id": unknown_department_id,
                "reasoning": "The selected department handles this issue.",
            },
            ensure_ascii=False,
        )

        llm_client.chat.completions.create.return_value = self.make_completion(
            response_content
        )

        with pytest.raises(
            TicketRoutingError,
            match="not available",
        ):
            await routing_connector.route(
                ticket_text=BUG_REPORT,
                departments=list_departments,
            )

    @pytest.mark.asyncio
    async def test_route_rejects_empty_title(
        self,
        routing_connector: OpenRouterTicketRoutingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Reject an LLM response with an empty ticket title."""
        response_content = json.dumps(
            {
                "title": "   ",
                "department_id": list_departments[0].id,
                "reasoning": "The selected department handles this issue.",
            }
        )

        llm_client.chat.completions.create.return_value = self.make_completion(
            response_content
        )

        with pytest.raises(
            TicketRoutingError,
            match="title must not be empty",
        ):
            await routing_connector.route(
                ticket_text=BUG_REPORT,
                departments=list_departments,
            )

    @pytest.mark.asyncio
    async def test_route_rejects_empty_reasoning(
        self,
        routing_connector: OpenRouterTicketRoutingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Reject an LLM response without department selection reasoning."""
        response_content = json.dumps(
            {
                "title": "Ошибка авторизации",
                "department_id": list_departments[0].id,
                "reasoning": "   ",
            },
            ensure_ascii=False,
        )

        llm_client.chat.completions.create.return_value = self.make_completion(
            response_content
        )

        with pytest.raises(
            TicketRoutingError,
            match="reasoning must not be empty",
        ):
            await routing_connector.route(
                ticket_text=BUG_REPORT,
                departments=list_departments,
            )

    @pytest.mark.asyncio
    async def test_route_rejects_truncated_response(
        self,
        routing_connector: OpenRouterTicketRoutingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Reject a completion interrupted by the output token limit."""
        llm_client.chat.completions.create.return_value = self.make_completion(
            content='{"title": "Ошибка',
            finish_reason="length",
        )

        with pytest.raises(
            TicketRoutingError,
            match="truncated",
        ):
            await routing_connector.route(
                ticket_text=BUG_REPORT,
                departments=list_departments,
            )

    @pytest.mark.asyncio
    async def test_route_rejects_empty_response(
        self,
        routing_connector: OpenRouterTicketRoutingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Reject an LLM response without message content."""
        llm_client.chat.completions.create.return_value = self.make_completion(
            content=None
        )

        with pytest.raises(
            TicketRoutingError,
            match="empty response",
        ):
            await routing_connector.route(
                ticket_text=BUG_REPORT,
                departments=list_departments,
            )

    @pytest.mark.asyncio
    async def test_route_rejects_empty_ticket(
        self,
        routing_connector: OpenRouterTicketRoutingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Reject an empty bug report before calling the LLM."""
        with pytest.raises(
            ValueError,
            match="Ticket text must not be empty",
        ):
            await routing_connector.route(
                ticket_text="   ",
                departments=list_departments,
            )

        llm_client.chat.completions.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_route_rejects_empty_department_list(
        self,
        routing_connector: OpenRouterTicketRoutingConnector,
        llm_client: MagicMock,
    ) -> None:
        """Reject an empty department list before calling the LLM."""
        with pytest.raises(
            ValueError,
            match="Department list must not be empty",
        ):
            await routing_connector.route(
                ticket_text=BUG_REPORT,
                departments=[],
            )

        llm_client.chat.completions.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_route_rejects_duplicate_department_ids(
        self,
        routing_connector: OpenRouterTicketRoutingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Reject a department list containing duplicate IDs."""
        duplicate_departments = [
            list_departments[0],
            list_departments[0].model_copy(update={"name": "Another Department"}),
        ]

        with pytest.raises(
            ValueError,
            match="Department IDs must be unique",
        ):
            await routing_connector.route(
                ticket_text=BUG_REPORT,
                departments=duplicate_departments,
            )

        llm_client.chat.completions.create.assert_not_awaited()
