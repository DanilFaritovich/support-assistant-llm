import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.connectors.openrouter_ticket_drafting_connector import (
    OpenRouterTicketDraftingConnector,
    TicketDraftingError,
)
from app.schemas.department import Department
from app.schemas.ticket_draft import TicketDraft

BUG_REPORT = "При отправке POST-запроса на /api/auth/login сервер возвращает HTTP 500."

DESCRIPTION_TEMPLATE = "Issue:\nSteps to reproduce:\nActual result:\nExpected result:"


class TestOpenRouterTicketDraftingConnector:
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
    async def test_draft_parses_valid_json(
        self,
        drafting_connector: OpenRouterTicketDraftingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Parse a valid LLM response into the ticket draft schema."""
        department = list_departments[0]

        expected_description = (
            "Issue:\n"
            "Пользователь не может авторизоваться.\n\n"
            "Steps to reproduce:\n"
            "Отправить POST-запрос на /api/auth/login.\n\n"
            "Actual result:\n"
            "Сервер возвращает HTTP 500.\n\n"
            "Expected result:\n"
            "Не указано."
        )

        response_content = json.dumps(
            {"description": expected_description},
            ensure_ascii=False,
        )

        llm_client.chat.completions.create.return_value = self.make_completion(
            response_content
        )

        result = await drafting_connector.draft(
            ticket_text=BUG_REPORT,
            department=department,
            template=DESCRIPTION_TEMPLATE,
        )

        assert isinstance(result, TicketDraft)
        assert result.description == expected_description

        llm_client.chat.completions.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_draft_sends_one_ticket_department_and_template(
        self,
        drafting_connector: OpenRouterTicketDraftingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Send one bug report, its department, and the description template."""
        department = list_departments[0]

        llm_client.chat.completions.create.return_value = self.make_completion(
            json.dumps({"description": "Generated bug report description."})
        )

        await drafting_connector.draft(
            ticket_text=BUG_REPORT,
            department=department,
            template=DESCRIPTION_TEMPLATE,
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
        assert messages[0]["content"].strip()

        assert messages[1]["role"] == "user"

        user_content = messages[1]["content"]

        assert user_content.startswith(
            "Generate a description for the following single bug report."
        )

        input_json = user_content.split(
            "Input data:\n",
            maxsplit=1,
        )[1]

        input_data = json.loads(input_json)

        assert input_data == {
            "department": department.model_dump(mode="json"),
            "template": DESCRIPTION_TEMPLATE,
            "original_ticket": BUG_REPORT,
        }

    @pytest.mark.asyncio
    async def test_draft_rejects_invalid_json(
        self,
        drafting_connector: OpenRouterTicketDraftingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Reject an LLM response that is not valid JSON."""
        llm_client.chat.completions.create.return_value = self.make_completion(
            "This is not JSON."
        )

        with pytest.raises(
            TicketDraftingError,
            match="does not match",
        ):
            await drafting_connector.draft(
                ticket_text=BUG_REPORT,
                department=list_departments[0],
                template=DESCRIPTION_TEMPLATE,
            )

    @pytest.mark.asyncio
    async def test_draft_rejects_missing_description(
        self,
        drafting_connector: OpenRouterTicketDraftingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Reject a JSON response without the required description field."""
        llm_client.chat.completions.create.return_value = self.make_completion("{}")

        with pytest.raises(
            TicketDraftingError,
            match="does not match",
        ):
            await drafting_connector.draft(
                ticket_text=BUG_REPORT,
                department=list_departments[0],
                template=DESCRIPTION_TEMPLATE,
            )

    @pytest.mark.asyncio
    async def test_draft_rejects_unexpected_fields(
        self,
        drafting_connector: OpenRouterTicketDraftingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        llm_client.chat.completions.create.return_value = self.make_completion(
            json.dumps({"description": "Valid", "extra": "not allowed"})
        )

        with pytest.raises(TicketDraftingError, match="does not match"):
            await drafting_connector.draft(
                ticket_text=BUG_REPORT,
                department=list_departments[0],
                template=DESCRIPTION_TEMPLATE,
            )

    @pytest.mark.asyncio
    async def test_draft_rejects_invalid_description_type(
        self,
        drafting_connector: OpenRouterTicketDraftingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Reject a description that is not a string."""
        llm_client.chat.completions.create.return_value = self.make_completion(
            json.dumps({"description": ["Unexpected", "list"]})
        )

        with pytest.raises(
            TicketDraftingError,
            match="does not match",
        ):
            await drafting_connector.draft(
                ticket_text=BUG_REPORT,
                department=list_departments[0],
                template=DESCRIPTION_TEMPLATE,
            )

    @pytest.mark.asyncio
    async def test_draft_rejects_empty_description(
        self,
        drafting_connector: OpenRouterTicketDraftingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Reject a generated description containing only whitespace."""
        llm_client.chat.completions.create.return_value = self.make_completion(
            json.dumps({"description": "   "})
        )

        with pytest.raises(
            TicketDraftingError,
            match="description must not be empty",
        ):
            await drafting_connector.draft(
                ticket_text=BUG_REPORT,
                department=list_departments[0],
                template=DESCRIPTION_TEMPLATE,
            )

    @pytest.mark.asyncio
    async def test_draft_rejects_empty_ticket(
        self,
        drafting_connector: OpenRouterTicketDraftingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Reject an empty ticket before calling the LLM."""
        with pytest.raises(
            ValueError,
            match="Ticket text must not be empty",
        ):
            await drafting_connector.draft(
                ticket_text="   ",
                department=list_departments[0],
                template=DESCRIPTION_TEMPLATE,
            )

        llm_client.chat.completions.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_draft_rejects_empty_template(
        self,
        drafting_connector: OpenRouterTicketDraftingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Reject an empty template before calling the LLM."""
        with pytest.raises(
            ValueError,
            match="Description template must not be empty",
        ):
            await drafting_connector.draft(
                ticket_text=BUG_REPORT,
                department=list_departments[0],
                template="   ",
            )

        llm_client.chat.completions.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_draft_rejects_truncated_response(
        self,
        drafting_connector: OpenRouterTicketDraftingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Reject an LLM response interrupted by the output token limit."""
        llm_client.chat.completions.create.return_value = self.make_completion(
            content='{"description": "Incomplete',
            finish_reason="length",
        )

        with pytest.raises(
            TicketDraftingError,
            match="truncated",
        ):
            await drafting_connector.draft(
                ticket_text=BUG_REPORT,
                department=list_departments[0],
                template=DESCRIPTION_TEMPLATE,
            )

    @pytest.mark.asyncio
    async def test_draft_rejects_empty_llm_response(
        self,
        drafting_connector: OpenRouterTicketDraftingConnector,
        llm_client: MagicMock,
        list_departments: list[Department],
    ) -> None:
        """Reject an LLM response without message content."""
        llm_client.chat.completions.create.return_value = self.make_completion(
            content=None
        )

        with pytest.raises(
            TicketDraftingError,
            match="empty response",
        ):
            await drafting_connector.draft(
                ticket_text=BUG_REPORT,
                department=list_departments[0],
                template=DESCRIPTION_TEMPLATE,
            )
