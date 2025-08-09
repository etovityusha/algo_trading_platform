from __future__ import annotations

from decimal import Decimal

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
