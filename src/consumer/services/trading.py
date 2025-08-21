import logging

from core.clients.interface import AbstractWriteClient
from src.consumer.uow import UoWSession
from src.core.clients.dto import BuyResponse
from src.core.dto import TradingSignal
from src.core.enums import ActionEnum

logger = logging.getLogger(__name__)


class TradingService:
    def __init__(self, client: AbstractWriteClient, uow_session: UoWSession):
        self.client = client
        self.uow_session = uow_session

    async def process_signal(self, signal: TradingSignal) -> BuyResponse | None:
        if signal.action != ActionEnum.BUY:
            logger.info(f"Skipping non-buy signal {signal.symbol}")
            return None
        # Guard: if we have UoW configured, avoid duplicate open deals for same symbol+source
        has_open = await self.uow_session.deals.has_open_buy_for_symbol_by_source(signal.symbol, signal.source)
        if has_open:
            logger.info(f"Skipping buy for {signal.symbol}: open position already exists")
            return None

        response = await self.client.buy(
            symbol=signal.symbol,
            usdt_amount=signal.amount,
            take_profit_percent=signal.take_profit,
            stop_loss_percent=signal.stop_loss,
        )
        logger.info(f"Buy signal processed for {signal.symbol}; order id: {response.order_id}")
        await self.uow_session.deals.create_from_buy(signal=signal, response=response)
        await self.uow_session.commit()
        return response
