from sqlalchemy.ext.asyncio import AsyncSession

from backtester.repositories.backtest_repository import BacktestRepository


class BacktestUnitOfWork:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.backtest = BacktestRepository(session)

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def close(self) -> None:
        await self._session.close()
