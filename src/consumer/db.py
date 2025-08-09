from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.consumer.config.settings import ConsumerSettings

_settings = ConsumerSettings()


def _ensure_async_dsn(dsn: str) -> str:
    if "+" in dsn:
        return dsn
    if dsn.startswith("postgresql://"):
        return dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    return dsn


ASYNC_DATABASE_URI: str = _ensure_async_dsn(_settings.SQLALCHEMY_DATABASE_URI)
engine: AsyncEngine = create_async_engine(
    ASYNC_DATABASE_URI,
    pool_pre_ping=True,
    connect_args={"server_settings": {"timezone": "UTC"}},
)
SessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return SessionFactory
