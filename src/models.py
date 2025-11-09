import datetime
from uuid import UUID

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, Index, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)
from sqlalchemy.types import TypeDecorator
from uuid_extensions import uuid7

from core.enums import ActionEnum


class Base(DeclarativeBase):
    pass


class UTCNaiveDateTime(TypeDecorator):
    """Store datetimes as naive UTC in the DB (TIMESTAMP WITHOUT TIME ZONE).

    - On bind: convert aware datetimes to UTC and drop tzinfo; leave naive as-is.
    - On result: return the naive datetime as stored.
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime.datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is not None:
            return value.astimezone(datetime.UTC).replace(tzinfo=None)
        return value

    def process_result_value(self, value: datetime.datetime | None, dialect):
        return value


class Deal(Base):
    __tablename__ = "deal"

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
        unique=True,
        nullable=False,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(UTCNaiveDateTime(), server_default=func.now(), nullable=False)

    external_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False)

    qty: Mapped[Numeric | None] = mapped_column(Numeric(20, 10), nullable=False)
    price: Mapped[float | None] = mapped_column(Float, nullable=False)
    take_profit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_take_profit_executed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_stop_loss_executed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_manually_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sell_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    action: Mapped[ActionEnum] = mapped_column(Enum(ActionEnum), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)


class BacktestResult(Base):
    __tablename__ = "backtest_result"
    __table_args__ = (Index("ix_backtest_result_params_hash", "params_hash"),)

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
        unique=True,
        nullable=False,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(UTCNaiveDateTime(), server_default=func.now(), nullable=False)

    # Backtest parameters for duplicate detection
    params_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    strategy_name: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[datetime.datetime] = mapped_column(UTCNaiveDateTime(), nullable=False)
    end_date: Mapped[datetime.datetime] = mapped_column(UTCNaiveDateTime(), nullable=False)
    signal_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    candle_interval: Mapped[str] = mapped_column(String, nullable=False)
    lookback_periods: Mapped[int] = mapped_column(Integer, nullable=False)
    position_size_usd: Mapped[float] = mapped_column(Float, nullable=False)
    strategy_params: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Results
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False)
    total_return_percent: Mapped[float] = mapped_column(Float, nullable=False)
    win_rate: Mapped[float] = mapped_column(Float, nullable=False)
    total_income: Mapped[float] = mapped_column(Float, nullable=False)
    total_volume: Mapped[float] = mapped_column(Float, nullable=False)
    trades_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # Detailed trades information
