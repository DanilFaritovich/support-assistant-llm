from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.openrouter_ticket_drafting_connector import (
    OpenRouterTicketDraftingConnector,
)
from app.connectors.openrouter_ticket_routing_connector import (
    OpenRouterTicketRoutingConnector,
)
from app.ports.department_port import DepartmentRepository
from app.ports.llm_quota_port import LLMQuotaPort
from app.repositories.sqlalchemy_department_repository import (
    SqlAlchemyDepartmentRepository,
)
from app.schemas.workspace import WorkspaceData
from app.services.department_service import DepartmentService
from app.services.ticket_drafting_service import TicketDraftingService
from app.services.ticket_processing_service import TicketProcessingService
from app.services.ticket_routing_service import TicketRoutingService
from app.services.workspace_service import WorkspaceDepartmentRepository


def create_department_service(
    session: AsyncSession,
    workspace_data: WorkspaceData | None = None,
) -> DepartmentService:
    """Create a department service for the provided database session."""
    repository: DepartmentRepository = (
        WorkspaceDepartmentRepository(workspace_data)
        if workspace_data is not None
        else SqlAlchemyDepartmentRepository(session)
    )

    return DepartmentService(
        department_repository=repository,
    )


def create_ticket_routing_service(
    llm_client: AsyncOpenAI,
    llm_models: list[str],
    llm_quota: LLMQuotaPort,
) -> TicketRoutingService:
    """Create a service for selecting the responsible department."""
    connector = OpenRouterTicketRoutingConnector(
        client=llm_client,
        models=llm_models,
    )

    return TicketRoutingService(
        ticket_routing=connector,
        llm_quota=llm_quota,
    )


def create_ticket_processing_service(
    session: AsyncSession,
    llm_client: AsyncOpenAI,
    llm_models: list[str],
    llm_quota: LLMQuotaPort,
    workspace_data: WorkspaceData | None = None,
) -> TicketProcessingService:
    """Create a service for generating a ticket description."""
    department_service = create_department_service(session, workspace_data)

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
        llm_quota=llm_quota,
    )
