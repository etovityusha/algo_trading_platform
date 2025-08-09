from __future__ import annotations

from decimal import Decimal
import datetime as _dt

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

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
            return value.astimezone(_dt.timezone.utc).replace(tzinfo=None)

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
