from sqlalchemy import delete, func, insert, literal, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.dml import ReturningInsert, ReturningUpdate

from app.db.models.workspace import WorkspaceORM
from app.schemas.workspace import WorkspaceData, WorkspaceState


class SqlAlchemyWorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, token_hash: str, now: int) -> WorkspaceState | None:
        row = await self._session.scalar(
            select(WorkspaceORM).where(
                WorkspaceORM.token_hash == token_hash,
                WorkspaceORM.expires_at > now,
            )
        )
        if row is None:
            return None
        return WorkspaceState(
            data=WorkspaceData.model_validate_json(row.data),
            revision=row.revision,
            personalized=True,
        )

    async def save(
        self,
        token_hash: str,
        data: WorkspaceData,
        revision: int,
        now: int,
        expires_at: int,
        max_count: int,
    ) -> bool:
        # One adapter operation owns its complete compare-and-swap transaction.
        await self._session.execute(
            delete(WorkspaceORM).where(WorkspaceORM.expires_at <= now)
        )
        statement: ReturningInsert[tuple[str]] | ReturningUpdate[tuple[str]]
        if revision == 0:
            count = select(func.count()).select_from(WorkspaceORM).scalar_subquery()
            statement = (
                insert(WorkspaceORM)
                .from_select(
                    ["token_hash", "data", "revision", "expires_at"],
                    select(
                        literal(token_hash),
                        literal(data.model_dump_json()),
                        literal(1),
                        literal(expires_at),
                    ).where(count < max_count),
                )
                .returning(WorkspaceORM.token_hash)
            )
        else:
            statement = (
                update(WorkspaceORM)
                .where(
                    WorkspaceORM.token_hash == token_hash,
                    WorkspaceORM.revision == revision,
                    WorkspaceORM.expires_at > now,
                )
                .values(
                    data=data.model_dump_json(),
                    revision=revision + 1,
                    expires_at=expires_at,
                )
                .returning(WorkspaceORM.token_hash)
            )
        changed = (await self._session.execute(statement)).scalar_one_or_none()
        await self._session.commit()
        return changed is not None
