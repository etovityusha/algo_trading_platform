import logging

from src.core.clients.bybit_async import BybitAsyncClient
from src.core.clients.dto import BuyResponse
from src.core.dto import TradingSignal
from src.core.enums import ActionEnum

logger = logging.getLogger(__name__)


class TradingService:
    def __init__(self, client: BybitAsyncClient):
        self.client = client

    async def process_signal(self, signal: TradingSignal) -> BuyResponse | None:
        if signal.action != ActionEnum.BUY:
            logger.info(f"Skipping non-buy signal {signal.symbol}")
            return None
        response = await self.client.buy(
            symbol=signal.symbol,
            usdt_amount=signal.amount,
            take_profit_percent=signal.take_profit,
            stop_loss_percent=signal.stop_loss,
        )
        logger.info(
            f"Buy signal processed for {signal.symbol}; order id: {response.order_id}"
        )
        return response
