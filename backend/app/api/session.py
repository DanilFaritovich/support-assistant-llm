from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def get_session(
    request: Request,
) -> AsyncIterator[AsyncSession]:
    """Provide a database session for the current HTTP request."""
    session_factory: async_sessionmaker[AsyncSession] = (
        request.app.state.session_factory
    )

    async with session_factory() as session:
        yield session
