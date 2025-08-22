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
        """Update existing BUY position with sell_price and mark as closed."""
        # Get the open position first
        open_position = await self.get_open_position(signal.symbol, signal.source)
        if not open_position:
            raise ValueError(f"No open position found for {signal.symbol} from {signal.source}")

        # Update the existing BUY position with sell price and mark as closed
        stmt = (
            update(Deal)
            .where(Deal.id == open_position.id)
            .values(sell_price=self._decimal_to_float(response.price), is_manually_closed=True)
        )
        await self.session.execute(stmt)
        await self.session.flush()

        # Refresh the object to get updated data
        await self.session.refresh(open_position)
        return open_position

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
            .where(Deal.action == ActionEnum.BUY)
            .where(Deal.is_manually_closed.is_(True))
            .where(Deal.sell_price.is_not(None))
            .where(Deal.created_at >= cutoff_time)
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_all_open_positions(self) -> list[Deal]:
        """Get all open BUY positions that haven't been closed by TP/SL or manually."""
        stmt = (
            select(Deal)
            .where(Deal.action == ActionEnum.BUY)
            .where(Deal.is_take_profit_executed.is_(False))
            .where(Deal.is_stop_loss_executed.is_(False))
            .where(Deal.is_manually_closed.is_(False))
            .order_by(Deal.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_take_profit_executed(self, deal_id: str, sell_price: float) -> None:
        """Mark a deal as take profit executed."""
        stmt = update(Deal).where(Deal.id == deal_id).values(is_take_profit_executed=True, sell_price=sell_price)
        await self.session.execute(stmt)
        await self.session.flush()

    async def mark_stop_loss_executed(self, deal_id: str, sell_price: float) -> None:
        """Mark a deal as stop loss executed."""
        stmt = update(Deal).where(Deal.id == deal_id).values(is_stop_loss_executed=True, sell_price=sell_price)
        await self.session.execute(stmt)
        await self.session.flush()

    async def mark_manually_closed(self, deal_id: str) -> None:
        """Mark a deal as manually closed."""
        stmt = update(Deal).where(Deal.id == deal_id).values(is_manually_closed=True)
        await self.session.execute(stmt)
        await self.session.flush()
