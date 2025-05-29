from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional, List
from .dto import BuyResponse, Candle


class AbstractReadOnlyClient(ABC):
    @abstractmethod
    async def get_candles(
        self, symbol: str, interval: str = "15", limit: int = 200
    ) -> List[Candle]:
        pass

    @abstractmethod
    async def get_instrument_info(self, symbol: str) -> dict:
        pass

    @abstractmethod
    async def get_ticker_price(self, symbol: str) -> Decimal:
        pass


class AbstractWriteClient(ABC):

    @abstractmethod
    async def buy(
        self,
        symbol: str,
        usdt_amount: Decimal,
        stop_loss_percent: Optional[float] = None,
        take_profit_percent: Optional[float] = None,
    ) -> BuyResponse:
        pass
