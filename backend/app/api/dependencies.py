from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, HTTPException, Request
from openai import AsyncOpenAI
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.contracts import DepartmentReader, TicketProcessor, TicketRouter
from app.composition import (
    create_department_service,
    create_ticket_processing_service,
    create_ticket_routing_service,
)
from app.core.config import settings
from app.ports.llm_quota_port import LLMQuotaPort


async def get_session(
    request: Request,
) -> AsyncIterator[AsyncSession]:
    """Provide a database session for the current HTTP request."""
    session_factory: async_sessionmaker[AsyncSession] = (
        request.app.state.session_factory
    )

    async with session_factory() as session:
        yield session


def get_client_id(request: Request) -> str:
    """Return the trusted transport-derived client identity."""
    return request.client.host if request.client is not None else "unknown"


def get_llm_quota(request: Request) -> LLMQuotaPort:
    """Provide the shared quota adapter for LLM-backed operations."""
    return cast(LLMQuotaPort, request.app.state.llm_quota)


async def ensure_quota_store_ready(request: Request) -> None:
    """Reject readiness when the required Redis quota store is unavailable."""
    redis_client: Redis | None = request.app.state.redis_client
    if redis_client is None:
        return

    try:
        await redis_client.ping()
    except RedisError as exc:
        raise HTTPException(
            status_code=503,
            detail="Shared quota storage is unavailable.",
        ) from exc


def get_department_reader(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DepartmentReader:
    """Provide a department reader for the current request."""
    return create_department_service(session)


def get_ticket_router(
    request: Request,
    llm_quota: Annotated[LLMQuotaPort, Depends(get_llm_quota)],
) -> TicketRouter:
    """Provide the ticket routing service for the current request."""
    llm_client: AsyncOpenAI | None = request.app.state.llm_client
    llm_models = settings.openrouter_model_list

    if llm_client is None:
        raise HTTPException(
            status_code=503,
            detail="OpenRouter is not configured. Set OPENROUTER_API_KEY.",
        )

    return create_ticket_routing_service(
        llm_client=llm_client,
        llm_models=llm_models,
        llm_quota=llm_quota,
    )


def get_ticket_processor(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    llm_quota: Annotated[LLMQuotaPort, Depends(get_llm_quota)],
) -> TicketProcessor:
    """Provide the ticket description generation use case."""
    llm_client: AsyncOpenAI | None = request.app.state.llm_client
    llm_models = settings.openrouter_model_list

    if llm_client is None:
        raise HTTPException(
            status_code=503,
            detail="OpenRouter is not configured. Set OPENROUTER_API_KEY.",
        )

    return create_ticket_processing_service(
        session=session,
        llm_client=llm_client,
        llm_models=llm_models,
        llm_quota=llm_quota,
    )
