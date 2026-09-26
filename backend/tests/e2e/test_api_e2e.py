import importlib
import json
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
import pytest
import pytest_asyncio
from openai import AsyncOpenAI
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.db.models.department import DepartmentORM
from app.exceptions import LLMQuotaExceededError
from app.schemas.department import Department

main_module = importlib.import_module("app.main")

BUG_REPORT = "При отправке POST-запроса на /api/auth/login сервер возвращает HTTP 500."

DESCRIPTION_TEMPLATE = "Issue:\nSteps to reproduce:\nActual result:\nExpected result:"

EXPECTED_TITLE = "Ошибка авторизации: HTTP 500"

EXPECTED_REASONING = "The selected department handles server-side application APIs."

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

type APIClientFixture = tuple[
    httpx.AsyncClient,
    list[Department],
    list[str],
]


class FakeLLMQuota:
    """Provide deterministic process-local quota state only for API tests."""

    def __init__(self, per_minute: int = 10) -> None:
        self._per_minute = per_minute
        self._requests: dict[str, int] = {}

    async def consume(self, client_id: str) -> None:
        count = self._requests.get(client_id, 0)
        if count >= self._per_minute:
            raise LLMQuotaExceededError(retry_after=60)
        self._requests[client_id] = count + 1


@pytest_asyncio.fixture
async def api_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[APIClientFixture]:
    """Create the API with a temporary database and a mocked LLM endpoint."""
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"

    monkeypatch.setattr(
        main_module.settings,
        "database_url",
        database_url,
    )
    monkeypatch.setattr(
        main_module.settings,
        "openrouter_api_key",
        SecretStr("test-key"),
    )
    monkeypatch.setattr(
        main_module.settings,
        "openrouter_models",
        "test-model:free",
    )

    async def skip_demo_seed(session: object) -> int:
        return 0

    monkeypatch.setattr(main_module, "seed_demo_departments", skip_demo_seed)

    departments = [
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

    selected_department = departments[1]

    engine = create_async_engine(database_url)

    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(
            bind=engine,
            expire_on_commit=False,
        )

        async with session_factory() as session:
            session.add_all(
                [
                    DepartmentORM(
                        id=department.id,
                        name=department.name,
                        description=department.description,
                    )
                    for department in departments
                ]
            )
            await session.commit()

        llm_requests: list[str] = []

        def handle_llm_request(
            request: httpx.Request,
        ) -> httpx.Response:
            """Emulate ticket routing and description generation."""
            assert request.method == "POST"
            assert request.url.path == "/v1/chat/completions"

            payload = json.loads(request.content)

            assert payload["model"] == "test-model:free"
            assert payload["temperature"] == 0.0
            assert "models" not in payload
            assert payload["provider"] == {"require_parameters": True}
            assert payload["response_format"]["type"] == "json_schema"

            messages = payload["messages"]

            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[0]["content"].strip()
            assert messages[1]["role"] == "user"

            user_content = messages[1]["content"]

            if user_content.startswith("Available IT departments:\n"):
                departments_section, ticket_text = user_content.split(
                    "\n\nOriginal bug report:\n",
                    maxsplit=1,
                )

                assert ticket_text == BUG_REPORT

                departments_json = departments_section.removeprefix(
                    "Available IT departments:\n"
                )

                assert json.loads(departments_json) == [
                    department.model_dump(mode="json") for department in departments
                ]

                llm_requests.append("routing")

                response_content = json.dumps(
                    {
                        "title": EXPECTED_TITLE,
                        "department_id": selected_department.id,
                        "reasoning": EXPECTED_REASONING,
                    },
                    ensure_ascii=False,
                )

            elif user_content.startswith(
                "Generate a description for the following single bug report."
            ):
                input_json = user_content.split(
                    "Input data:\n",
                    maxsplit=1,
                )[1]

                assert json.loads(input_json) == {
                    "department": selected_department.model_dump(mode="json"),
                    "template": DESCRIPTION_TEMPLATE,
                    "original_ticket": BUG_REPORT,
                }

                llm_requests.append("drafting")

                response_content = json.dumps(
                    {
                        "description": EXPECTED_DESCRIPTION,
                    },
                    ensure_ascii=False,
                )

            else:
                raise AssertionError("The application sent an unexpected LLM request.")

            return httpx.Response(
                status_code=200,
                json={
                    "id": f"chatcmpl-test-{len(llm_requests)}",
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

        llm_client = AsyncOpenAI(
            api_key="not-needed",
            base_url="https://llm.example.test/v1",
            http_client=httpx.AsyncClient(
                transport=httpx.MockTransport(handle_llm_request),
            ),
            max_retries=0,
        )

        monkeypatch.setattr(
            main_module,
            "create_llm_client",
            lambda: llm_client,
        )

        app = main_module.create_app(llm_quota_override=FakeLLMQuota())

        # ASGITransport does not start the FastAPI lifespan automatically.
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://testserver",
            ) as client:
                yield client, departments, llm_requests

    finally:
        await engine.dispose()


@pytest.mark.asyncio
class TestSupportAssistantAPI:
    async def test_health_returns_request_correlation_id(
        self,
        api_client: APIClientFixture,
    ) -> None:
        """Return readiness and a generated request correlation ID."""
        client, _, llm_requests = api_client

        response = await client.get("/api/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        assert len(response.headers["X-Request-ID"]) == 32
        assert llm_requests == []

    async def test_get_departments_returns_database_records(
        self,
        api_client: APIClientFixture,
    ) -> None:
        """Return departments from SQLite without invoking the LLM."""
        client, departments, llm_requests = api_client

        response = await client.get("/api/departments")

        assert response.status_code == 200
        assert response.json() == [
            department.model_dump(mode="json") for department in departments
        ]
        assert llm_requests == []

    async def test_route_ticket_returns_selected_department(
        self,
        api_client: APIClientFixture,
    ) -> None:
        """Route a ticket without generating its description."""
        client, departments, llm_requests = api_client

        response = await client.post(
            "/api/tickets/route",
            json={
                "ticket_text": BUG_REPORT,
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "title": EXPECTED_TITLE,
            "department_id": departments[1].id,
            "department_name": departments[1].name,
            "reasoning": EXPECTED_REASONING,
        }

        assert llm_requests == ["routing"]

    async def test_process_ticket_generates_description_without_routing(
        self,
        api_client: APIClientFixture,
    ) -> None:
        """Generate a description using an already selected department."""
        client, departments, llm_requests = api_client

        response = await client.post(
            "/api/tickets/process",
            json={
                "ticket_text": BUG_REPORT,
                "department_id": departments[1].id,
                "template": DESCRIPTION_TEMPLATE,
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "description": EXPECTED_DESCRIPTION,
        }

        assert llm_requests == ["drafting"]

    async def test_route_then_process_ticket(
        self,
        api_client: APIClientFixture,
    ) -> None:
        """Complete the user workflow in two separate HTTP requests."""
        client, departments, llm_requests = api_client

        routing_response = await client.post(
            "/api/tickets/route",
            json={
                "ticket_text": BUG_REPORT,
            },
        )

        assert routing_response.status_code == 200

        routing_data = routing_response.json()

        assert routing_data == {
            "title": EXPECTED_TITLE,
            "department_id": departments[1].id,
            "department_name": departments[1].name,
            "reasoning": EXPECTED_REASONING,
        }

        # The user finds the template after seeing the routing result.
        processing_response = await client.post(
            "/api/tickets/process",
            json={
                "ticket_text": BUG_REPORT,
                "department_id": routing_data["department_id"],
                "template": DESCRIPTION_TEMPLATE,
            },
        )

        assert processing_response.status_code == 200
        assert processing_response.json() == {
            "description": EXPECTED_DESCRIPTION,
        }

        assert llm_requests == ["routing", "drafting"]

    async def test_process_ticket_rejects_unknown_department(
        self,
        api_client: APIClientFixture,
    ) -> None:
        """Return HTTP 404 without invoking the LLM for an unknown department."""
        client, _, llm_requests = api_client

        response = await client.post(
            "/api/tickets/process",
            json={
                "ticket_text": BUG_REPORT,
                "department_id": 999,
                "template": DESCRIPTION_TEMPLATE,
            },
        )

        assert response.status_code == 404
        assert response.json() == {
            "detail": "The selected department does not exist.",
        }

        assert llm_requests == []

    async def test_limits_llm_operations_without_limiting_technical_endpoints(
        self,
        api_client: APIClientFixture,
    ) -> None:
        """Return HTTP 429 after ten shared LLM operations from one IP."""
        client, departments, llm_requests = api_client

        for _ in range(10):
            response = await client.post(
                "/api/tickets/route",
                json={"ticket_text": BUG_REPORT},
            )
            assert response.status_code == 200

        limited_response = await client.post(
            "/api/tickets/process",
            json={
                "ticket_text": BUG_REPORT,
                "department_id": departments[1].id,
                "template": DESCRIPTION_TEMPLATE,
            },
        )

        assert limited_response.status_code == 429
        assert limited_response.json() == {
            "detail": "Too many LLM requests. Please try again later.",
        }
        assert 1 <= int(limited_response.headers["Retry-After"]) <= 60
        assert llm_requests == ["routing"] * 10

        health_response = await client.get("/api/health")
        departments_response = await client.get("/api/departments")

        assert health_response.status_code == 200
        assert departments_response.status_code == 200
        assert llm_requests == ["routing"] * 10

    async def test_rejects_oversized_input_without_invoking_the_llm(
        self,
        api_client: APIClientFixture,
    ) -> None:
        """Validate ticket and template limits at the HTTP boundary."""
        client, departments, llm_requests = api_client

        routing_response = await client.post(
            "/api/tickets/route",
            json={"ticket_text": "x" * 4001},
        )
        processing_ticket_response = await client.post(
            "/api/tickets/process",
            json={
                "ticket_text": "x" * 4001,
                "department_id": departments[1].id,
                "template": DESCRIPTION_TEMPLATE,
            },
        )
        processing_template_response = await client.post(
            "/api/tickets/process",
            json={
                "ticket_text": BUG_REPORT,
                "department_id": departments[1].id,
                "template": "x" * 2001,
            },
        )

        assert routing_response.status_code == 422
        assert processing_ticket_response.status_code == 422
        assert processing_template_response.status_code == 422
        assert llm_requests == []
