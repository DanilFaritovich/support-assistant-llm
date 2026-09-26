import logging
from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from typing import cast

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from openai import APIError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.middleware import RequestContextMiddleware
from app.api.routes import router
from app.connectors.llm_client import create_llm_client
from app.connectors.openrouter_ticket_drafting_connector import TicketDraftingError
from app.connectors.openrouter_ticket_routing_connector import TicketRoutingError
from app.connectors.redis_llm_quota_adapter import RedisLLMQuotaAdapter
from app.core.config import settings
from app.core.logging import configure_logging
from app.db.seed import seed_demo_departments
from app.exceptions import (
    DepartmentNotFoundError,
    InvalidDepartmentSelectionError,
    LLMQuotaExceededError,
    LLMQuotaUnavailableError,
    NoDepartmentsAvailableError,
)
from app.ports.llm_quota_port import LLMQuotaPort

configure_logging(
    level=settings.log_level,
    log_format=settings.log_format,
    service_name=settings.service_name,
    environment=settings.environment,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and release shared application resources."""
    engine = create_async_engine(settings.database_url)

    async with AsyncExitStack() as stack:
        stack.push_async_callback(engine.dispose)

        app.state.session_factory = async_sessionmaker(
            bind=engine,
            expire_on_commit=False,
        )
        app.state.llm_client = None
        app.state.redis_client = None

        quota_override: LLMQuotaPort | None = app.state.llm_quota_override
        if quota_override is not None:
            app.state.llm_quota = quota_override
        else:
            redis_client = Redis.from_url(
                settings.redis_url.get_secret_value(),
                decode_responses=True,
            )
            stack.push_async_callback(redis_client.aclose)
            await redis_client.ping()

            app.state.redis_client = redis_client
            app.state.llm_quota = RedisLLMQuotaAdapter(
                redis_client=redis_client,
                per_minute=settings.llm_rate_limit_per_minute,
                per_day=settings.llm_rate_limit_per_day,
            )

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
        "Ticket processing failed.",
        extra={
            "event": "ticket_processing_failed",
            "error_type": type(exc).__name__,
        },
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


async def handle_llm_quota_exceeded(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Map application quota exhaustion to HTTP 429."""
    quota_error = cast(LLMQuotaExceededError, exc)
    logger.warning(
        "LLM operation quota exceeded.",
        extra={
            "event": "llm_quota_exceeded",
            "retry_after": quota_error.retry_after,
        },
    )
    return JSONResponse(
        status_code=429,
        headers={"Retry-After": str(quota_error.retry_after)},
        content={"detail": "Too many LLM requests. Please try again later."},
    )


async def handle_llm_quota_unavailable(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Map shared quota storage failures to a safe HTTP response."""
    logger.error(
        "LLM operation rejected because shared quota storage is unavailable.",
        extra={"event": "llm_quota_unavailable"},
    )
    return JSONResponse(
        status_code=503,
        content={"detail": "LLM request limiting is temporarily unavailable."},
    )


def create_app(llm_quota_override: LLMQuotaPort | None = None) -> FastAPI:
    """Create and configure the Support Assistant API."""
    app = FastAPI(
        title="Support Assistant API",
        lifespan=lifespan,
    )
    app.state.llm_quota_override = llm_quota_override

    app.add_middleware(RequestContextMiddleware)
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
    app.add_exception_handler(
        LLMQuotaExceededError,
        handle_llm_quota_exceeded,
    )
    app.add_exception_handler(
        LLMQuotaUnavailableError,
        handle_llm_quota_unavailable,
    )

    return app


app = create_app()
