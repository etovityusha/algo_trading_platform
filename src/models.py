import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, Float, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)
from uuid_extensions import uuid7

from src.core.enums import ActionEnum


class Base(DeclarativeBase):
    pass


class Deal(Base):
    __tablename__ = "deal"

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
        unique=True,
        nullable=False,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    external_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False)

    qty: Mapped[Numeric | None] = mapped_column(Numeric(20, 10), nullable=False)
    price: Mapped[float | None] = mapped_column(Float, nullable=False)
    take_profit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_take_profit_executed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_stop_loss_executed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    action: Mapped[ActionEnum] = mapped_column(Enum(ActionEnum), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
