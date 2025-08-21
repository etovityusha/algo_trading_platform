import logging

from src.core.clients.interface import AbstractReadOnlyClient
from src.core.enums import PositionInternalStatus
from src.models import Deal

logger = logging.getLogger(__name__)


class OrderProcessor:
    """Simplified service for determining position status based only on current price"""

    def __init__(self, read_client: AbstractReadOnlyClient):
        self._read_client = read_client

    async def get_position_status(self, position: Deal) -> PositionInternalStatus:
        logger.debug(f"Checking position {position.id} for {position.symbol}")

        current_price = await self._read_client.get_ticker_price(position.symbol)
        logger.debug(f"Current price for {position.symbol}: {current_price}")

        if position.stop_loss_price and current_price <= position.stop_loss_price:
            logger.info(f"Position {position.id} hit Stop Loss: {current_price} <= {position.stop_loss_price}")
            return PositionInternalStatus.CLOSED_BY_SL
        if position.take_profit_price and current_price >= position.take_profit_price:
            logger.info(f"Position {position.id} hit Take Profit: {current_price} >= {position.take_profit_price}")
            return PositionInternalStatus.CLOSED_BY_TP
        logger.debug(f"Position {position.id} is still open")
        return PositionInternalStatus.OPEN
