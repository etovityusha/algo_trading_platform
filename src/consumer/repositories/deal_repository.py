from __future__ import annotations

import datetime as _dt
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.clients.dto import BuyResponse
from src.core.dto import TradingSignal
from src.core.enums import ActionEnum
from src.models import Deal


class DealRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @classmethod
    def _decimal_to_float(cls, value: Decimal | None) -> float | None:
        if value is None:
            return None
        return float(value)

    async def create_from_buy(self, signal: TradingSignal, response: BuyResponse) -> Deal:
        deal = Deal(
            external_id=response.order_id,
            symbol=response.symbol,
            qty=response.qty,
            price=self._decimal_to_float(response.price),
            take_profit_price=self._decimal_to_float(response.take_profit_price),
            stop_loss_price=self._decimal_to_float(response.stop_loss_price),
            action=ActionEnum.BUY,
            source=signal.source,
        )
        self.session.add(deal)
        await self.session.flush()
        return deal

    async def list_by_period(
        self,
        start_inclusive: _dt.datetime,
        end_exclusive: _dt.datetime,
        *,
        symbol: str | None = None,
        source: str | None = None,
    ) -> list[Deal]:
        """Return deals created in [start_inclusive, end_exclusive).

        Optional filters by symbol and/or source can be applied.
        """

        # Normalize to naive UTC (column is TIMESTAMP WITHOUT TIME ZONE)
        def _to_naive_utc(value: _dt.datetime) -> _dt.datetime:
            if value.tzinfo is None:
                return value
            return value.astimezone(_dt.UTC).replace(tzinfo=None)

        start_inclusive = _to_naive_utc(start_inclusive)
        end_exclusive = _to_naive_utc(end_exclusive)

        stmt = (
            select(Deal)
            .where(Deal.created_at >= start_inclusive)
            .where(Deal.created_at < end_exclusive)
            .order_by(Deal.created_at.asc())
        )
        if symbol is not None:
            stmt = stmt.where(Deal.symbol == symbol)
        if source is not None:
            stmt = stmt.where(Deal.source == source)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def has_open_buy_for_symbol_by_source(self, symbol: str, source: str) -> bool:
        """Return True if there is a BUY deal for symbol without TP/SL execution or manual close."""
        stmt = (
            select(Deal.id)
            .where(Deal.symbol == symbol)
            .where(Deal.action == ActionEnum.BUY)
            .where(Deal.is_take_profit_executed.is_(False))
            .where(Deal.is_stop_loss_executed.is_(False))
            .where(Deal.is_manually_closed.is_(False))
            .where(Deal.source == source)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def close_position(self, signal: TradingSignal, response: BuyResponse) -> Deal:
        """Create a SELL deal that closes an open position and mark the original position as closed."""
        # First, mark the original BUY position as manually closed
        await self._mark_position_as_closed(signal.symbol, signal.source)

        # Create SELL deal record
        deal = Deal(
            external_id=response.order_id,
            symbol=response.symbol,
            qty=response.qty,
            price=self._decimal_to_float(response.price),
            take_profit_price=None,  # SELL deals don't have TP/SL
            stop_loss_price=None,
            action=ActionEnum.SELL,
            source=signal.source,
        )
        self.session.add(deal)
        await self.session.flush()
        return deal

    async def get_open_position(self, symbol: str, source: str) -> Deal | None:
        """Get open BUY position for symbol and source."""
        stmt = (
            select(Deal)
            .where(Deal.symbol == symbol)
            .where(Deal.action == ActionEnum.BUY)
            .where(Deal.is_take_profit_executed.is_(False))
            .where(Deal.is_stop_loss_executed.is_(False))
            .where(Deal.is_manually_closed.is_(False))
            .where(Deal.source == source)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _mark_position_as_closed(self, symbol: str, source: str) -> None:
        """Mark the open BUY position as manually closed."""
        stmt = (
            update(Deal)
            .where(Deal.symbol == symbol)
            .where(Deal.action == ActionEnum.BUY)
            .where(Deal.is_take_profit_executed.is_(False))
            .where(Deal.is_stop_loss_executed.is_(False))
            .where(Deal.is_manually_closed.is_(False))
            .where(Deal.source == source)
            .values(is_manually_closed=True)
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def has_recently_closed_position(self, symbol: str, source: str, minutes: int = 60) -> bool:
        """Check if there's a recently closed position to prevent immediate reopening."""
        cutoff_time = _dt.datetime.now(_dt.UTC).replace(tzinfo=None) - _dt.timedelta(minutes=minutes)

        stmt = (
            select(Deal.id)
            .where(Deal.symbol == symbol)
            .where(Deal.source == source)
            .where(Deal.action == ActionEnum.SELL)
            .where(Deal.created_at >= cutoff_time)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
