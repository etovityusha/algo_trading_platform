import logging

from src.consumer.uow import UnitOfWork
from src.core.clients.bybit_async import BybitAsyncClient
from src.core.clients.dto import BuyResponse
from src.core.dto import TradingSignal
from src.core.enums import ActionEnum

logger = logging.getLogger(__name__)


class TradingService:
    def __init__(self, client: BybitAsyncClient, uow: UnitOfWork | None = None):
        self.client = client
        self.uow = uow

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
        logger.info(f"Buy signal processed for {signal.symbol}; order id: {response.order_id}")
        # persist deal if uow is configured
        if self.uow is not None:
            async with self.uow() as uow_session:
                await uow_session.deals.create_from_buy(signal=signal, response=response)
        return response
