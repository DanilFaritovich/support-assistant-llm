from typing import Protocol

from app.schemas.workspace import WorkspaceData, WorkspaceState


class WorkspaceRepository(Protocol):
    async def get(self, token_hash: str, now: int) -> WorkspaceState | None: ...

    async def save(
        self,
        token_hash: str,
        data: WorkspaceData,
        revision: int,
        now: int,
        expires_at: int,
        max_count: int,
    ) -> bool:
        """Atomically compare the revision and persist one settings document.

        Return False on a conflict or exhausted workspace capacity.
        """
        ...
