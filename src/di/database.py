from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from configs import PostgresSettings
from consumer.uow import UnitOfWork, UoWSession


class DatabaseProvider(Provider):
    @provide(scope=Scope.APP)
    async def create_engine(self, cfg: PostgresSettings) -> AsyncEngine:
        def _ensure_async_dsn(dsn: str) -> str:
            if "+" in dsn:
                return dsn
            if dsn.startswith("postgresql://"):
                return dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
            return dsn

        async_dsn = _ensure_async_dsn(cfg.async_dsn)
        return create_async_engine(
            async_dsn,
            pool_pre_ping=True,
            connect_args={"server_settings": {"timezone": "UTC"}},
        )

    @provide(scope=Scope.APP)
    def create_session_factory(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(
            bind=engine,
            autoflush=False,
            expire_on_commit=False,
        )

    @provide(scope=Scope.REQUEST)
    def create_unit_of_work(self, session_factory: async_sessionmaker[AsyncSession]) -> UnitOfWork:
        return UnitOfWork(session_factory=session_factory)

    @provide(scope=Scope.REQUEST)
    async def create_uow_session(self, session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[UoWSession]:
        session: AsyncSession = session_factory()
        try:
            async with session.begin():
                yield UoWSession(session)
        finally:
            await session.close()
