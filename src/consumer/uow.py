from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.consumer.repositories.deal_repository import DealRepository


class UnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @asynccontextmanager
    async def __call__(self) -> AsyncIterator[UoWSession]:
        session: AsyncSession = self._session_factory()
        try:
            async with session.begin():
                yield UoWSession(session)
        finally:
            await session.close()


class UoWSession:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.deals = DealRepository(session=session)

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()
