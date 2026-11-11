from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.api.workspace_dependencies import (
    COOKIE_NAME,
    get_guest_token,
    get_workspace_service,
)
from app.core.config import settings
from app.schemas.workspace import WorkspaceData, WorkspaceState
from app.services.workspace_service import WorkspaceConflictError, WorkspaceService

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


def require_workspace_request(request: Request) -> None:
    # A custom header forces a browser preflight; this API does not allow CORS.
    if (
        request.headers.get("x-workspace-request") != "1"
        or request.headers.get("sec-fetch-site") == "cross-site"
    ):
        raise HTTPException(403, "A same-origin workspace request is required.")


class SaveWorkspaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data: WorkspaceData
    revision: int = Field(ge=0, le=2147483647)


@router.get("", response_model=WorkspaceState)
async def read_workspace(
    service: Annotated[WorkspaceService, Depends(get_workspace_service)],
    token: Annotated[str | None, Depends(get_guest_token)],
) -> WorkspaceState:
    return await service.read(token)


@router.get("/defaults", response_model=WorkspaceState)
async def read_workspace_defaults(
    service: Annotated[WorkspaceService, Depends(get_workspace_service)],
) -> WorkspaceState:
    return await service.defaults()


@router.put(
    "", response_model=WorkspaceState, dependencies=[Depends(require_workspace_request)]
)
async def save_workspace(
    payload: SaveWorkspaceRequest,
    response: Response,
    service: Annotated[WorkspaceService, Depends(get_workspace_service)],
    token: Annotated[str | None, Depends(get_guest_token)],
) -> WorkspaceState:
    try:
        state, new_token = await service.save(token, payload.data, payload.revision)
    except WorkspaceConflictError as exc:
        raise HTTPException(
            409, "Workspace changed, expired, or storage is full. Reload before saving."
        ) from exc
    response.set_cookie(
        COOKIE_NAME,
        new_token,
        max_age=settings.guest_workspace_ttl_days * 86400,
        secure=settings.guest_cookie_secure,
        httponly=True,
        samesite="lax",
        path="/api",
    )
    return state
