import json

import httpx
import pytest
from openai import AsyncOpenAI

from app.connectors.openrouter_ticket_drafting_connector import (
    OpenRouterTicketDraftingConnector,
)
from app.schemas.department import Department
from app.schemas.ticket_draft import TicketDraft
from app.services.ticket_drafting_service import TicketDraftingService

BUG_REPORT = "При отправке POST-запроса на /api/auth/login сервер возвращает HTTP 500."

DESCRIPTION_TEMPLATE = "Issue:\nSteps to reproduce:\nActual result:\nExpected result:"

EXPECTED_DESCRIPTION = (
    "Issue:\n"
    "Пользователь не может авторизоваться.\n\n"
    "Steps to reproduce:\n"
    "Отправить POST-запрос на /api/auth/login.\n\n"
    "Actual result:\n"
    "Сервер возвращает HTTP 500.\n\n"
    "Expected result:\n"
    "Не указано."
)


class TestTicketDraftingServiceIntegration:
    @pytest.mark.asyncio
    async def test_drafts_one_ticket_using_mock_api(
        self,
        list_departments: list[Department],
    ) -> None:
        """Generate a ticket description using a mocked HTTP LLM endpoint."""
        department = list_departments[0]
        request_count = 0

        def handle_llm_request(
            request: httpx.Request,
        ) -> httpx.Response:
            nonlocal request_count
            request_count += 1

            assert request.method == "POST"
            assert request.url.path == "/v1/chat/completions"

            payload = json.loads(request.content)

            assert payload["model"] == "test-model:free"
            assert "models" not in payload
            assert payload["provider"] == {"require_parameters": True}
            assert payload["temperature"] == 0.0

            messages = payload["messages"]

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

            response_content = json.dumps(
                {"description": EXPECTED_DESCRIPTION},
                ensure_ascii=False,
            )

            return httpx.Response(
                status_code=200,
                json={
                    "id": "chatcmpl-test",
                    "object": "chat.completion",
                    "created": 1,
                    "model": "test-model",
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": response_content,
                            },
                            "finish_reason": "stop",
                        }
                    ],
                },
            )

        transport = httpx.MockTransport(handle_llm_request)

        async with AsyncOpenAI(
            api_key="not-needed",
            base_url="https://llm.example.test/v1",
            http_client=httpx.AsyncClient(transport=transport),
            max_retries=0,
        ) as llm_client:
            drafting_connector = OpenRouterTicketDraftingConnector(
                client=llm_client,
                models=["test-model:free"],
            )

            service = TicketDraftingService(
                ticket_drafting=drafting_connector,
            )

            result = await service.draft(
                ticket_text=BUG_REPORT,
                department=department,
                template=DESCRIPTION_TEMPLATE,
            )

        assert isinstance(result, TicketDraft)
        assert result.description == EXPECTED_DESCRIPTION
        assert request_count == 1
