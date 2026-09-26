import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from openai import APIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.rate_limiting import InMemoryLLMRateLimiter
from app.api.routes import router
from app.connectors.llm_client import create_llm_client
from app.connectors.openrouter_ticket_drafting_connector import TicketDraftingError
from app.connectors.openrouter_ticket_routing_connector import TicketRoutingError
from app.core.config import settings
from app.db.seed import seed_demo_departments
from app.exceptions import (
    DepartmentNotFoundError,
    InvalidDepartmentSelectionError,
    NoDepartmentsAvailableError,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and release shared application resources."""
    engine = create_async_engine(settings.database_url)
    app.state.llm_rate_limiter = InMemoryLLMRateLimiter(
        per_minute=settings.llm_rate_limit_per_minute,
        per_day=settings.llm_rate_limit_per_day,
    )

    async with AsyncExitStack() as stack:
        stack.push_async_callback(engine.dispose)

        app.state.session_factory = async_sessionmaker(
            bind=engine,
            expire_on_commit=False,
        )
        app.state.llm_client = None

        async with app.state.session_factory() as session:
            await seed_demo_departments(session)

        if settings.openrouter_api_key is not None:
            app.state.llm_client = await stack.enter_async_context(create_llm_client())

            logger.info("OpenRouter client initialized.")
        else:
            logger.warning(
                "OpenRouter is not configured. Ticket processing is unavailable."
            )

        logger.info("Support Assistant API started.")

        try:
            yield
        finally:
            logger.info("Support Assistant API is shutting down.")


async def handle_llm_error(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Return a safe HTTP response when LLM processing fails."""
    logger.warning(
        "Ticket processing failed: error_type=%s.",
        type(exc).__name__,
    )

    return JSONResponse(
        status_code=502,
        content={
            "detail": (
                "Free OpenRouter models are temporarily unavailable or returned "
                "an invalid response. Please try again later."
            ),
        },
    )


async def handle_no_departments(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Return an HTTP response when no departments are available."""
    logger.warning("Ticket processing failed: no departments are available.")

    return JSONResponse(
        status_code=503,
        content={
            "detail": "No departments are available for ticket processing.",
        },
    )


async def handle_invalid_department(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Return an HTTP response for an unavailable department."""
    logger.warning("Ticket processing failed: selected department is unavailable.")

    return JSONResponse(
        status_code=502,
        content={
            "detail": "The selected department is not available.",
        },
    )


async def handle_department_not_found(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Return an HTTP response when the selected department is missing."""
    logger.warning("Ticket processing failed: selected department does not exist.")

    return JSONResponse(
        status_code=404,
        content={
            "detail": "The selected department does not exist.",
        },
    )


def create_app() -> FastAPI:
    """Create and configure the Support Assistant API."""
    app = FastAPI(
        title="Support Assistant API",
        lifespan=lifespan,
    )

    app.include_router(router)

    app.add_exception_handler(
        TicketRoutingError,
        handle_llm_error,
    )
    app.add_exception_handler(
        TicketDraftingError,
        handle_llm_error,
    )
    app.add_exception_handler(
        APIError,
        handle_llm_error,
    )

    app.add_exception_handler(
        NoDepartmentsAvailableError,
        handle_no_departments,
    )
    app.add_exception_handler(
        InvalidDepartmentSelectionError,
        handle_invalid_department,
    )

    app.add_exception_handler(
        DepartmentNotFoundError,
        handle_department_not_found,
    )

    return app


app = create_app()
