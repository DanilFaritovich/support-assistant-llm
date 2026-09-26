import json
from unittest.mock import MagicMock

import httpx
import pytest
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.openrouter_ticket_drafting_connector import (
    OpenRouterTicketDraftingConnector,
)
from app.db.models.department import DepartmentORM
from app.repositories.sqlalchemy_department_repository import (
    SqlAlchemyDepartmentRepository,
)
from app.schemas.department import Department
from app.schemas.ticket_draft import TicketDraft
from app.services.department_service import DepartmentService
from app.services.ticket_drafting_service import TicketDraftingService
from app.services.ticket_processing_service import TicketProcessingService

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


class TestTicketProcessingServiceIntegration:
    @pytest.mark.asyncio
    async def test_generates_description_using_selected_department_and_mock_api(
        self,
        session: AsyncSession,
        llm_quota: MagicMock,
    ) -> None:
        """
        Generate a ticket description using a department stored in SQLite
        and a mocked LLM API response.
        """
        # Arrange: create isolated test departments in SQLite.
        expected_departments = [
            Department(
                id=101,
                name="Test Frontend Department",
                description="Responsible for user interfaces.",
            ),
            Department(
                id=202,
                name="Test Backend Department",
                description="Responsible for server-side application APIs.",
            ),
        ]

        session.add_all(
            [
                DepartmentORM(
                    id=department.id,
                    name=department.name,
                    description=department.description,
                )
                for department in expected_departments
            ]
        )
        await session.commit()

        selected_department = expected_departments[1]
        llm_requests: list[httpx.Request] = []

        def handle_llm_request(request: httpx.Request) -> httpx.Response:
            """Emulate a description generation response from the LLM API."""
            llm_requests.append(request)

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
                "department": selected_department.model_dump(mode="json"),
                "template": DESCRIPTION_TEMPLATE,
                "original_ticket": BUG_REPORT,
            }

            response_content = json.dumps(
                {
                    "description": EXPECTED_DESCRIPTION,
                },
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
            # Arrange: create the real repository and application services.
            department_repository = SqlAlchemyDepartmentRepository(session)

            department_service = DepartmentService(
                department_repository=department_repository,
            )

            drafting_connector = OpenRouterTicketDraftingConnector(
                client=llm_client,
                models=["test-model:free"],
            )

            drafting_service = TicketDraftingService(
                ticket_drafting=drafting_connector,
            )

            processing_service = TicketProcessingService(
                department_service=department_service,
                ticket_drafting_service=drafting_service,
                llm_quota=llm_quota,
            )

            # Act: generate a description for the previously selected department.
            result = await processing_service.process(
                ticket_text=BUG_REPORT,
                department_id=selected_department.id,
                template=DESCRIPTION_TEMPLATE,
                client_id="192.0.2.1",
            )

        # Assert: verify the generated description.
        assert isinstance(result, TicketDraft)
        assert result.description == EXPECTED_DESCRIPTION

        # Only drafting is performed. The department is not routed again.
        assert len(llm_requests) == 1
