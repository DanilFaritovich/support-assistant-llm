import re
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.session import get_session
from app.core.config import settings
from app.core.workspace_defaults import load_workspace_defaults
from app.repositories.sqlalchemy_department_repository import (
    SqlAlchemyDepartmentRepository,
)
from app.repositories.sqlalchemy_workspace_repository import (
    SqlAlchemyWorkspaceRepository,
)
from app.services.workspace_service import WorkspaceService

COOKIE_NAME = "support_guest"


def get_guest_token(request: Request) -> str | None:
    token = request.cookies.get(COOKIE_NAME, "")
    return token if re.fullmatch(r"[a-zA-Z0-9_-]{43}", token) else None


def get_workspace_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> WorkspaceService:
    return WorkspaceService(
        SqlAlchemyWorkspaceRepository(session),
        SqlAlchemyDepartmentRepository(session),
        load_workspace_defaults(),
        settings.guest_workspace_ttl_days * 86400,
        settings.guest_workspace_max_count,
    )
