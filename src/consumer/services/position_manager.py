import logging
from typing import Protocol

from consumer.uow import UnitOfWork
from core.clients.interface import AbstractReadOnlyClient
from core.enums import PositionInternalStatus
from core.services.order_processor import OrderProcessor
from models import Deal

logger = logging.getLogger(__name__)


class UnitOfWorkFactory(Protocol):
    """Protocol for UnitOfWork factory"""

    def __call__(self) -> UnitOfWork: ...


class PositionManagerService:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        read_client: AbstractReadOnlyClient,
    ) -> None:
        self._uow_factory = uow_factory
        self._read_client = read_client
        self._order_processor = OrderProcessor(read_client)

    async def handle_open_positions(self) -> None:
        """Process all open positions and update their status."""
        logger.info("Starting open positions processing")

        async with self._uow_factory() as uow_session:
            open_positions = await uow_session.deals.get_all_open_positions()
            logger.info(f"Found {len(open_positions)} open positions")

            if not open_positions:
                logger.info("No open positions to process")
                return

            for position in open_positions:
                status = await self._order_processor.get_position_status(position)
                await self._handle_position_status(uow_session, position, status)

    async def _handle_position_status(self, uow_session, position: Deal, status: PositionInternalStatus) -> None:
        position_id = str(position.id)

        if status == PositionInternalStatus.CLOSED_BY_TP:
            logger.info(f"Position {position_id} closed by Take Profit")
            # Get current price for sell_price
            current_price = float(await self._read_client.get_ticker_price(position.symbol))
            await uow_session.deals.mark_take_profit_executed(position_id, current_price)

        elif status == PositionInternalStatus.CLOSED_BY_SL:
            logger.info(f"Position {position_id} closed by Stop Loss")
            # Get current price for sell_price
            current_price = float(await self._read_client.get_ticker_price(position.symbol))
            await uow_session.deals.mark_stop_loss_executed(position_id, current_price)

        elif status == PositionInternalStatus.OPEN:
            logger.debug(f"Position {position_id} is still open")
            # No DB update needed

    async def process_single_position(self, position: Deal) -> PositionInternalStatus:
        """Process a single position and update its status"""
        async with self._uow_factory() as uow_session:
            status = await self._order_processor.get_position_status(position)
            await self._handle_position_status(uow_session, position, status)
            return status
