from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.openrouter_ticket_drafting_connector import (
    OpenRouterTicketDraftingConnector,
)
from app.connectors.openrouter_ticket_routing_connector import (
    OpenRouterTicketRoutingConnector,
)
from app.repositories.sqlalchemy_department_repository import (
    SqlAlchemyDepartmentRepository,
)
from app.services.department_service import DepartmentService
from app.services.ticket_drafting_service import TicketDraftingService
from app.services.ticket_processing_service import TicketProcessingService
from app.services.ticket_routing_service import TicketRoutingService


def create_department_service(
    session: AsyncSession,
) -> DepartmentService:
    """Create a department service for the provided database session."""
    repository = SqlAlchemyDepartmentRepository(session)

    return DepartmentService(
        department_repository=repository,
    )


def create_ticket_routing_service(
    llm_client: AsyncOpenAI,
    llm_models: list[str],
) -> TicketRoutingService:
    """Create a service for selecting the responsible department."""
    connector = OpenRouterTicketRoutingConnector(
        client=llm_client,
        models=llm_models,
    )

    return TicketRoutingService(
        ticket_routing=connector,
    )


def create_ticket_processing_service(
    session: AsyncSession,
    llm_client: AsyncOpenAI,
    llm_models: list[str],
) -> TicketProcessingService:
    """Create a service for generating a ticket description."""
    department_service = create_department_service(session)

    drafting_connector = OpenRouterTicketDraftingConnector(
        client=llm_client,
        models=llm_models,
    )

    drafting_service = TicketDraftingService(
        ticket_drafting=drafting_connector,
    )

    return TicketProcessingService(
        department_service=department_service,
        ticket_drafting_service=drafting_service,
    )
