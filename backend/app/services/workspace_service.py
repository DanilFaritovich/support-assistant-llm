import hashlib
import secrets
import time
from collections.abc import Callable

from app.ports.department_port import DepartmentRepository
from app.ports.workspace_port import WorkspaceRepository
from app.schemas.department import Department
from app.schemas.workspace import (
    WorkspaceData,
    WorkspaceDefaults,
    WorkspaceDepartment,
    WorkspaceState,
)


class WorkspaceConflictError(Exception):
    """Settings changed, expired, or guest storage reached its capacity."""


class WorkspaceService:
    def __init__(
        self,
        repository: WorkspaceRepository,
        departments: DepartmentRepository,
        defaults: WorkspaceDefaults,
        ttl_seconds: int,
        max_count: int,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._repository = repository
        self._departments = departments
        self._defaults = defaults
        self._ttl = ttl_seconds
        self._max_count = max_count
        self._clock = clock

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    async def defaults(self) -> WorkspaceState:
        data = WorkspaceData(
            departments=[
                WorkspaceDepartment.model_validate(item.model_dump())
                for item in await self._departments.get_all()
            ],
            **self._defaults.model_dump(),
        )
        return WorkspaceState(
            data=data,
            revision=0,
            personalized=False,
            retention_days=self._ttl // 86400,
        )

    async def read(self, token: str | None) -> WorkspaceState:
        if token:
            state = await self._repository.get(self._hash(token), int(self._clock()))
            if state is not None:
                state.retention_days = self._ttl // 86400
                return state
        return await self.defaults()

    async def save(
        self,
        token: str | None,
        data: WorkspaceData,
        revision: int,
    ) -> tuple[WorkspaceState, str]:
        now = int(self._clock())
        if revision == 0:
            # Never adopt a caller-supplied token for a newly created space.
            if token and await self._repository.get(self._hash(token), now) is not None:
                raise WorkspaceConflictError
            token = secrets.token_urlsafe(32)
        elif not token:
            raise WorkspaceConflictError
        assert token is not None
        saved = await self._repository.save(
            self._hash(token),
            data,
            revision,
            now,
            now + self._ttl,
            self._max_count,
        )
        if not saved:
            raise WorkspaceConflictError
        return WorkspaceState(
            data=data,
            revision=revision + 1,
            personalized=True,
            retention_days=self._ttl // 86400,
        ), token


class WorkspaceDepartmentRepository:
    """Resolve only departments in the current settings snapshot."""

    def __init__(self, data: WorkspaceData) -> None:
        self._data = data

    async def get_all(self) -> list[Department]:
        return [
            Department.model_validate(item.model_dump())
            for item in self._data.departments
        ]

    async def get_by_id(self, department_id: int) -> Department | None:
        return next(
            (item for item in await self.get_all() if item.id == department_id), None
        )
