import json

import httpx
import pytest
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.openrouter_ticket_routing_connector import (
    OpenRouterTicketRoutingConnector,
)
from app.db.models.department import DepartmentORM
from app.repositories.sqlalchemy_department_repository import (
    SqlAlchemyDepartmentRepository,
)
from app.schemas.department import Department
from app.schemas.ticket_routing import TicketRoutingResult
from app.services.department_service import DepartmentService
from app.services.ticket_routing_service import TicketRoutingService

BUG_REPORT = "При отправке POST-запроса на /api/auth/login сервер возвращает HTTP 500."


class TestTicketRoutingServiceIntegration:
    @pytest.mark.asyncio
    async def test_routes_one_bug_using_database_and_mock_api(
        self,
        session: AsyncSession,
        seeded_departments: list[DepartmentORM],
        list_departments: list[Department],
    ) -> None:
        """Route one bug using SQLite and a mocked HTTP LLM endpoint."""
        assert len(seeded_departments) == len(list_departments)

        selected_department = list_departments[0]
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
            assert messages[1]["role"] == "user"

            user_content = messages[1]["content"]

            departments_section, ticket_text = user_content.split(
                "\n\nOriginal bug report:\n",
                maxsplit=1,
            )

            assert ticket_text == BUG_REPORT

            departments_json = departments_section.removeprefix(
                "Available IT departments:\n"
            )

            assert json.loads(departments_json) == [
                department.model_dump(mode="json") for department in list_departments
            ]

            response_content = json.dumps(
                {
                    "title": "Ошибка авторизации: HTTP 500",
                    "department_id": selected_department.id,
                    "reasoning": (
                        "The selected department handles the reported issue."
                    ),
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
            department_repository = SqlAlchemyDepartmentRepository(session)

            department_service = DepartmentService(
                department_repository=department_repository,
            )

            departments = await department_service.get_all()

            routing_connector = OpenRouterTicketRoutingConnector(
                client=llm_client,
                models=["test-model:free"],
            )

            routing_service = TicketRoutingService(
                ticket_routing=routing_connector,
            )

            result = await routing_service.route(
                ticket_text=BUG_REPORT,
                departments=departments,
            )

        assert isinstance(result, TicketRoutingResult)
        assert result.title == "Ошибка авторизации: HTTP 500"
        assert result.department_id == selected_department.id
        assert result.reasoning == (
            "The selected department handles the reported issue."
        )

        assert request_count == 1
