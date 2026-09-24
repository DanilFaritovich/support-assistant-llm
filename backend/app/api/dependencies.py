from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.contracts import DepartmentReader, TicketProcessor, TicketRouter
from app.composition import (
    create_department_service,
    create_ticket_processing_service,
    create_ticket_routing_service,
)
from app.core.config import settings


async def get_session(
    request: Request,
) -> AsyncIterator[AsyncSession]:
    """Provide a database session for the current HTTP request."""
    session_factory: async_sessionmaker[AsyncSession] = (
        request.app.state.session_factory
    )

    async with session_factory() as session:
        yield session


def get_department_reader(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DepartmentReader:
    """Provide a department reader for the current request."""
    return create_department_service(session)


def get_ticket_router(
    request: Request,
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
    )


def get_ticket_processor(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
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
    )
