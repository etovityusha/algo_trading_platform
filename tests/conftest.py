import os
import pathlib
import sys
from collections.abc import AsyncIterator, Iterator
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import delete, text
from sqlalchemy.engine import Engine as SyncEngine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _build_sync_dsn() -> str:
    uri = os.environ.get("SQLALCHEMY_DATABASE_URI")
    if uri:
        if uri.startswith("postgresql+asyncpg://"):
            uri = uri.replace("postgresql+asyncpg://", "postgresql://", 1)
        return uri
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "postgres")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def _build_async_dsn() -> str:
    uri = os.environ.get("SQLALCHEMY_DATABASE_URI")
    if uri:
        if uri.startswith("postgresql://"):
            uri = uri.replace("postgresql://", "postgresql+asyncpg://", 1)
        return uri
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "postgres")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


@pytest.fixture(scope="session", autouse=True)
def temp_database() -> Iterator[str]:
    """Create a temporary database for the whole test session and drop it at the end."""
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    port = os.environ.get("POSTGRES_PORT", "5432")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    maintenance_db = os.environ.get("POSTGRES_MAINTENANCE_DB", "postgres")

    admin_sync_dsn = f"postgresql://{user}:{password}@{host}:{port}/{maintenance_db}"
    db_name = f"test_{uuid4().hex}"

    admin_engine: SyncEngine = create_sync_engine(admin_sync_dsn, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {db_name}"))

    # Expose DSN for Alembic/tests in sync form; async fixtures will adapt it
    os.environ["SQLALCHEMY_DATABASE_URI"] = (
        f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
    )

    try:
        yield db_name
    finally:
        # Terminate connections and drop database
        with admin_engine.connect() as conn:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :dbname AND pid <> pg_backend_pid()"
                ),
                {"dbname": db_name},
            )
            conn.execute(text(f"DROP DATABASE IF EXISTS {db_name}"))
        admin_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def apply_migrations(temp_database: str) -> None:
    sync_dsn = _build_sync_dsn()
    os.environ["SQLALCHEMY_DATABASE_URI"] = sync_dsn
    alembic_cfg = Config(str(pathlib.Path(PROJECT_ROOT) / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")


@pytest.fixture(scope="session")
def async_engine(apply_migrations: None) -> Iterator[AsyncEngine]:
    engine = create_async_engine(_build_async_dsn(), pool_pre_ping=True)
    try:
        yield engine
    finally:
        import asyncio

        asyncio.get_event_loop().run_until_complete(engine.dispose())


@pytest.fixture(scope="session")
def async_session_factory(async_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=async_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
async def uow(async_session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[object]:
    from src.consumer.uow import UnitOfWork

    yield UnitOfWork(session_factory=async_session_factory)


@pytest.fixture(autouse=False)
async def clean_db(async_session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[None]:
    from src.models import Deal

    async with async_session_factory() as s:
        async with s.begin():
            await s.execute(delete(Deal))
    yield
