from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.contracts import DepartmentReader, TicketProcessor, TicketRouter
from app.api.dependencies import (
    ensure_quota_store_ready,
    get_client_id,
    get_department_reader,
    get_ticket_processor,
    get_ticket_router,
)
from app.api.schemas.department import DepartmentResponse
from app.api.schemas.ticket_processing import (
    TicketProcessingRequest,
    TicketProcessingResponse,
)
from app.api.schemas.ticket_routing import (
    TicketRoutingRequest,
    TicketRoutingResponse,
)
from app.exceptions import (
    InvalidDepartmentSelectionError,
    NoDepartmentsAvailableError,
)

router = APIRouter(prefix="/api")


@router.get(
    "/health",
    tags=["system"],
    dependencies=[Depends(ensure_quota_store_ready)],
)
async def health() -> dict[str, str]:
    """Return a lightweight health signal for containers and reverse proxies."""
    return {"status": "ok"}


@router.get(
    "/departments",
    response_model=list[DepartmentResponse],
    tags=["departments"],
)
async def get_departments(
    reader: Annotated[
        DepartmentReader,
        Depends(get_department_reader),
    ],
) -> list[DepartmentResponse]:
    """Return all available IT departments."""
    departments = await reader.get_all()

    return [
        DepartmentResponse.model_validate(department.model_dump())
        for department in departments
    ]


@router.post(
    "/tickets/route",
    response_model=TicketRoutingResponse,
    tags=["tickets"],
)
async def route_ticket(
    payload: TicketRoutingRequest,
    reader: Annotated[
        DepartmentReader,
        Depends(get_department_reader),
    ],
    ticket_router: Annotated[
        TicketRouter,
        Depends(get_ticket_router),
    ],
    client_id: Annotated[str, Depends(get_client_id)],
) -> TicketRoutingResponse:
    """Generate a title and select a department for a single ticket."""
    departments = await reader.get_all()

    if not departments:
        raise NoDepartmentsAvailableError(
            "No departments are available for ticket routing."
        )

    routing_result = await ticket_router.route(
        ticket_text=payload.ticket_text,
        departments=departments,
        client_id=client_id,
    )

    selected_department = next(
        (
            department
            for department in departments
            if department.id == routing_result.department_id
        ),
        None,
    )

    if selected_department is None:
        raise InvalidDepartmentSelectionError(
            "The selected department is not available."
        )

    return TicketRoutingResponse(
        title=routing_result.title,
        department_id=selected_department.id,
        department_name=selected_department.name,
        reasoning=routing_result.reasoning,
    )


@router.post(
    "/tickets/process",
    response_model=TicketProcessingResponse,
    tags=["tickets"],
)
async def process_ticket(
    payload: TicketProcessingRequest,
    processor: Annotated[
        TicketProcessor,
        Depends(get_ticket_processor),
    ],
    client_id: Annotated[str, Depends(get_client_id)],
) -> TicketProcessingResponse:
    """Generate a description for a previously routed ticket."""
    result = await processor.process(
        ticket_text=payload.ticket_text,
        department_id=payload.department_id,
        template=payload.template,
        client_id=client_id,
    )

    return TicketProcessingResponse.model_validate(result.model_dump())
