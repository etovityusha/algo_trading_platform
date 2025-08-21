import asyncio
import os
import pathlib
import sys
from collections.abc import AsyncIterator, Iterator
from decimal import Decimal
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine as create_sync_engine
from sqlalchemy import delete, select, text
from sqlalchemy.engine import Engine as SyncEngine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.consumer.services.position_manager import PositionManagerService
from src.consumer.uow import UnitOfWork, UoWSession
from src.core.clients.interface import AbstractReadOnlyClient
from src.core.enums import ActionEnum
from src.models import Deal

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


def _admin_sync_dsn() -> str:
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    port = os.environ.get("POSTGRES_PORT", "5432")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    maintenance_db = os.environ.get("POSTGRES_MAINTENANCE_DB", "postgres")
    return f"postgresql://{user}:{password}@{host}:{port}/{maintenance_db}"


@pytest.fixture(scope="session", autouse=True)
def template_database() -> Iterator[str]:
    """Create a template database once per session, apply migrations, drop at end.

    Per-test databases will be cloned from this template using CREATE DATABASE ... TEMPLATE ...
    """
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    port = os.environ.get("POSTGRES_PORT", "5432")
    host = os.environ.get("POSTGRES_HOST", "localhost")

    admin_sync_dsn = _admin_sync_dsn()
    template_db_name = f"test_template_{uuid4().hex}"

    admin_engine: SyncEngine = create_sync_engine(admin_sync_dsn, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {template_db_name}"))

    # Run migrations against the template DB
    os.environ["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{user}:{password}@{host}:{port}/{template_db_name}"
    alembic_cfg = Config(str(pathlib.Path(PROJECT_ROOT) / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

    try:
        yield template_db_name
    finally:
        # Ensure no lingering connections and drop template DB
        with admin_engine.connect() as conn:
            conn.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :dbname AND pid <> pg_backend_pid()"
                ),
                {"dbname": template_db_name},
            )
            conn.execute(text(f"DROP DATABASE IF EXISTS {template_db_name}"))
        admin_engine.dispose()


@pytest.fixture()
def test_database(template_database: str) -> Iterator[str]:
    """Create a per-test database cloned from the template; drop after test."""
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    port = os.environ.get("POSTGRES_PORT", "5432")
    host = os.environ.get("POSTGRES_HOST", "localhost")

    admin_sync_dsn = _admin_sync_dsn()
    clone_db_name = f"test_{uuid4().hex}"

    admin_engine: SyncEngine = create_sync_engine(admin_sync_dsn, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f"CREATE DATABASE {clone_db_name} TEMPLATE {template_database}"))
        try:
            yield f"postgresql://{user}:{password}@{host}:{port}/{clone_db_name}"
        finally:
            conn.execute(text(f"DROP DATABASE {clone_db_name}"))
        admin_engine.dispose()


@pytest.fixture()
def async_engine(test_database: str) -> Iterator[AsyncEngine]:
    # Create async engine for the per-test database DSN
    async_dsn = test_database.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(
        async_dsn,
        pool_pre_ping=True,
        connect_args={"server_settings": {"timezone": "UTC"}},
    )
    try:
        yield engine
    finally:
        asyncio.get_event_loop().run_until_complete(engine.dispose())


@pytest.fixture()
def async_session_factory(async_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(bind=async_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture()
async def uow(async_session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[UnitOfWork]:
    yield UnitOfWork(session_factory=async_session_factory)


@pytest.fixture()
async def uow_session(async_session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[UoWSession]:
    session: AsyncSession = async_session_factory()
    try:
        async with session.begin():
            yield UoWSession(session)
    finally:
        await session.close()


@pytest.fixture()
def uow_factory(async_session_factory: async_sessionmaker[AsyncSession]) -> UnitOfWork:
    """Factory for creating UnitOfWork instances with proper session management"""
    return UnitOfWork(session_factory=async_session_factory)


class MockReadOnlyClient(AbstractReadOnlyClient):
    """Mock implementation of AbstractReadOnlyClient for testing"""

    def __init__(self):
        self.ticker_prices = {}

    def set_ticker_price(self, symbol: str, price: Decimal):
        """Set mock price for a symbol"""
        self.ticker_prices[symbol] = price

    async def get_ticker_price(self, symbol: str) -> Decimal:
        return self.ticker_prices.get(symbol, Decimal("100.0"))

    async def get_candles(self, symbol: str, interval: str = "15", limit: int = 200, start=None):
        return []

    async def get_instrument_info(self, symbol: str):
        return {}

    async def get_order_status(self, order_id: str, symbol: str):
        return None


@pytest.fixture
def mock_read_client():
    """Mock read client for testing"""
    return MockReadOnlyClient()


@pytest.fixture
async def position_manager_service(
    uow_factory: UnitOfWork, mock_read_client: MockReadOnlyClient
) -> PositionManagerService:
    """Position manager service with properly injected dependencies"""
    return PositionManagerService(uow_factory, mock_read_client)


class DataManager:
    """Helper class for managing test data across multiple transactions"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def create_deal(
        self,
        symbol: str = "BTCUSDT",
        qty: Decimal = Decimal("0.5"),
        price: float = 100.0,
        take_profit_price: float = 102.0,
        stop_loss_price: float = 98.0,
        action: ActionEnum = ActionEnum.BUY,
        source: str = "test_source",
        external_id: str = None,
    ) -> Deal:
        """Create a deal in a separate transaction"""
        deal = Deal(
            id=uuid4(),
            external_id=external_id or f"test_order_{uuid4().hex[:8]}",
            symbol=symbol,
            qty=qty,
            price=price,
            take_profit_price=take_profit_price,
            stop_loss_price=stop_loss_price,
            action=action,
            source=source,
        )

        async with self.session_factory() as session:
            session.add(deal)
            await session.flush()
            await session.commit()

        return deal

    async def get_deal(self, deal_id) -> Deal:
        """Get a deal by ID in a separate transaction"""
        async with self.session_factory() as session:
            result = await session.execute(select(Deal).where(Deal.id == deal_id))
            return result.scalar_one()

    async def create_multiple_deals(self, deals_data: list[dict]) -> list[Deal]:
        """Create multiple deals in a single transaction"""
        deals = []
        async with self.session_factory() as session:
            for deal_data in deals_data:
                deal = Deal(
                    id=uuid4(),
                    external_id=deal_data.get("external_id", f"test_order_{uuid4().hex[:8]}"),
                    symbol=deal_data.get("symbol", "BTCUSDT"),
                    qty=deal_data.get("qty", Decimal("0.5")),
                    price=deal_data.get("price", 100.0),
                    take_profit_price=deal_data.get("take_profit_price", 102.0),
                    stop_loss_price=deal_data.get("stop_loss_price", 98.0),
                    action=deal_data.get("action", ActionEnum.BUY),
                    source=deal_data.get("source", "test_source"),
                )
                deals.append(deal)
                session.add(deal)

            await session.flush()
            await session.commit()

        return deals


@pytest.fixture
def test_data_manager(async_session_factory: async_sessionmaker[AsyncSession]) -> DataManager:
    """Test data manager for creating test data across multiple transactions"""
    return DataManager(async_session_factory)


@pytest.fixture(autouse=False)
async def clean_db(async_session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[None]:
    async with async_session_factory() as s:
        async with s.begin():
            await s.execute(delete(Deal))
    yield
