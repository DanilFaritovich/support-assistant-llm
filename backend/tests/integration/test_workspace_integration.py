import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio
from openai import AsyncOpenAI
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base
from app.db.models.department import DepartmentORM
from app.db.models.workspace import WorkspaceORM
from app.main import create_app
from app.ports.llm_quota_port import LLMQuotaPort

HEADERS = {"X-Workspace-Request": "1"}


@pytest_asyncio.fixture
async def workspace_api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[tuple]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'workspace.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as session:
        session.add(
            DepartmentORM(id=1, name="Public demo", description="Public directory")
        )
        await session.commit()
    requests: list[dict] = []

    def llm_response(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requests.append(payload)
        content = payload["messages"][1]["content"]
        if content.startswith("Available IT departments:"):
            departments = json.loads(
                content.split("\n\nOriginal bug report:")[0].split("\n", 1)[1]
            )
            result = {
                "title": "Example",
                "department_id": departments[0]["id"],
                "reasoning": "Matches the scope.",
            }
        else:
            result = {"description": "Generated test description."}
        return httpx.Response(
            200,
            json={
                "id": "test",
                "object": "chat.completion",
                "created": 1,
                "model": "openrouter/free",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": json.dumps(result)},
                    }
                ],
            },
        )

    llm = AsyncOpenAI(
        api_key="test-key",
        base_url="https://llm.test/v1",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(llm_response)),
    )
    quota = AsyncMock(spec=LLMQuotaPort)
    app = create_app()
    app.state.session_factory = factory
    app.state.llm_client = llm
    app.state.llm_quota = quota
    app.state.redis_client = None
    monkeypatch.setattr(settings, "guest_cookie_secure", True)
    transport = httpx.ASGITransport(app=app)
    async with (
        httpx.AsyncClient(transport=transport, base_url="https://demo.test") as first,
        httpx.AsyncClient(transport=transport, base_url="https://demo.test") as second,
    ):
        try:
            yield first, second, factory, requests, quota
        finally:
            await llm.close()
            await engine.dispose()


async def initial_settings(client: httpx.AsyncClient) -> dict:
    response = await client.get("/api/workspace")
    assert response.status_code == 200
    return response.json()["data"]


async def save(
    client: httpx.AsyncClient, data: dict, revision: int = 0
) -> httpx.Response:
    return await client.put(
        "/api/workspace", headers=HEADERS, json={"data": data, "revision": revision}
    )


async def test_public_reads_do_not_create_spaces(workspace_api: tuple) -> None:
    first, _, factory, _, _ = workspace_api
    response = await first.get("/api/workspace")
    assert response.json()["revision"] == 0
    assert response.json()["personalized"] is False
    assert "no-store" in response.headers["cache-control"]
    assert not first.cookies
    await first.get("/api/departments")
    async with factory() as session:
        assert await session.scalar(select(func.count()).select_from(WorkspaceORM)) == 0


async def test_save_isolates_visitors_and_restores_from_cookie(
    workspace_api: tuple,
) -> None:
    first, second, factory, _, _ = workspace_api
    data = await initial_settings(first)
    data["departments"] = [
        {"id": 77, "name": "Private IT", "description": "Private scope"}
    ]
    data["examples"].append(
        {"id": "custom", "name": "My example", "text": "Example text", "locale": None}
    )
    response = await save(first, data)
    assert response.status_code == 200
    assert response.json()["revision"] == 1
    cookie_header = response.headers["set-cookie"]
    assert (
        "HttpOnly" in cookie_header
        and "Secure" in cookie_header
        and "SameSite=lax" in cookie_header
    )
    token = first.cookies.get("support_guest")
    assert len(token) == 43
    assert (await first.get("/api/workspace")).json()["data"] == response.json()["data"]
    assert (await first.get("/api/departments")).json() == data["departments"]
    assert (await second.get("/api/departments")).json()[0]["name"] == "Public demo"
    assert not (await second.get("/api/workspace")).json()["personalized"]
    async with factory() as session:
        row = await session.scalar(select(WorkspaceORM))
        assert token not in row.token_hash
        assert len(row.token_hash) == 64


async def test_routing_and_drafting_use_only_current_space(
    workspace_api: tuple,
) -> None:
    first, second, _, requests, quota = workspace_api
    data = await initial_settings(first)
    data["departments"] = [
        {"id": 77, "name": "My specialists", "description": "Handles my systems"}
    ]
    assert (await save(first, data)).status_code == 200
    routed = await first.post(
        "/api/tickets/route", json={"ticket_text": "Broken system"}
    )
    assert routed.status_code == 200
    assert routed.json()["department_id"] == 77
    assert "My specialists" in requests[0]["messages"][1]["content"]
    assert "Public demo" not in requests[0]["messages"][1]["content"]
    drafted = await first.post(
        "/api/tickets/process",
        json={
            "ticket_text": "Broken system",
            "department_id": 77,
            "template": "Summary:",
        },
    )
    assert drafted.status_code == 200
    assert "My specialists" in requests[1]["messages"][1]["content"]
    other = await second.post(
        "/api/tickets/process",
        json={
            "ticket_text": "Broken system",
            "department_id": 77,
            "template": "Summary:",
        },
    )
    assert other.status_code == 404
    public_id = await first.post(
        "/api/tickets/process",
        json={
            "ticket_text": "Broken system",
            "department_id": 1,
            "template": "Summary:",
        },
    )
    assert public_id.status_code == 404
    assert quota.consume.await_count == 2
    assert quota.consume.await_args_list[0] == quota.consume.await_args_list[1]


async def test_stale_save_never_overwrites_and_missing_cookie_does_not_recreate(
    workspace_api: tuple,
) -> None:
    first, second, _, _, _ = workspace_api
    data = await initial_settings(first)
    assert (await save(first, data)).status_code == 200
    data["templates"][0]["text"] = "New template"
    assert (await save(first, data, 1)).status_code == 200
    assert (await save(first, data, 1)).status_code == 409
    assert (await save(first, data, 0)).status_code == 409
    assert (await save(second, data, 2)).status_code == 409
    assert (await first.get("/api/workspace")).json()["revision"] == 2


async def test_expiration_and_capacity_are_enforced(
    workspace_api: tuple, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second, factory, _, _ = workspace_api
    monkeypatch.setattr(settings, "guest_workspace_max_count", 1)
    data = await initial_settings(first)
    assert (await save(first, data)).status_code == 200
    assert (await save(second, data)).status_code == 409
    async with factory() as session:
        await session.execute(update(WorkspaceORM).values(expires_at=0))
        await session.commit()
    assert (await first.get("/api/workspace")).json()["personalized"] is False
    assert (await save(first, data, 1)).status_code == 409
    assert (await save(second, data)).status_code == 200


async def test_csrf_and_import_validation_do_not_mutate_settings(
    workspace_api: tuple,
) -> None:
    first, _, _, _, _ = workspace_api
    data = await initial_settings(first)
    payload = {"data": data, "revision": 0}
    assert (await first.put("/api/workspace", json=payload)).status_code == 403
    assert (
        await first.put(
            "/api/workspace",
            json=payload,
            headers=HEADERS | {"Sec-Fetch-Site": "cross-site"},
        )
    ).status_code == 403
    data["default_template_id"] = "missing"
    assert (await save(first, data)).status_code == 422
    assert not first.cookies


async def test_restore_and_import_replace_whole_document(workspace_api: tuple) -> None:
    first, second, _, _, _ = workspace_api
    data = await initial_settings(first)
    data["templates"][0]["text"] = "Custom summary:"
    data["default_template_id"] = data["templates"][0]["id"]
    saved = (await save(first, data)).json()
    exported = saved["data"]
    assert (await save(second, exported)).status_code == 200
    defaults = (await first.get("/api/workspace/defaults")).json()["data"]
    assert (await save(first, defaults, 1)).status_code == 200
    assert (await first.get("/api/workspace")).json()["data"] == defaults
    assert (await second.get("/api/workspace")).json()["data"] == exported


async def test_concurrent_edits_compare_revisions_atomically(
    workspace_api: tuple,
) -> None:
    first, _, _, _, _ = workspace_api
    data = await initial_settings(first)
    assert (await save(first, data)).status_code == 200
    left = json.loads(json.dumps(data))
    right = json.loads(json.dumps(data))
    left["departments"][0]["name"] = "Left edit"
    right["departments"][0]["name"] = "Right edit"
    results = await asyncio.gather(save(first, left, 1), save(first, right, 1))
    assert sorted(response.status_code for response in results) == [200, 409]
    state = (await first.get("/api/workspace")).json()
    assert state["revision"] == 2
    winner = next(response for response in results if response.status_code == 200)
    assert state["data"] == winner.json()["data"]


async def test_new_workspace_does_not_adopt_a_supplied_unknown_token(
    workspace_api: tuple,
) -> None:
    first, _, _, _, _ = workspace_api
    supplied = "A" * 43
    first.cookies.set("support_guest", supplied, domain="demo.test", path="/api")
    data = await initial_settings(first)
    response = await save(first, data)
    assert response.status_code == 200
    assert first.cookies.get("support_guest") != supplied


async def test_retention_configuration_matches_cookie_and_api(
    workspace_api: tuple, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, _, _, _, _ = workspace_api
    monkeypatch.setattr(settings, "guest_workspace_ttl_days", 7)
    data = await initial_settings(first)
    response = await save(first, data)
    assert response.json()["retention_days"] == 7
    assert "Max-Age=604800" in response.headers["set-cookie"]
    assert (await first.get("/api/workspace")).json()["retention_days"] == 7
