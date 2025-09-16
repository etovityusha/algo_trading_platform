import logging
from decimal import Decimal

from consumer.uow import UoWSession
from core.clients.dto import BuyResponse
from core.clients.interface import AbstractWriteClient
from core.dto import PositionStatus, TradingSignal
from core.enums import ActionEnum

logger = logging.getLogger(__name__)


class TradingService:
    def __init__(self, client: AbstractWriteClient, uow_session: UoWSession):
        self.client = client
        self.uow_session = uow_session

    async def process_signal(self, signal: TradingSignal) -> BuyResponse | None:
        if signal.action == ActionEnum.NOTHING:
            logger.info(f"Skipping NOTHING signal for {signal.symbol}")
            return None

        if signal.action == ActionEnum.BUY:
            return await self._process_buy_signal(signal)
        elif signal.action == ActionEnum.SELL:
            return await self._process_sell_signal(signal)

        logger.warning(f"Unknown action {signal.action} for {signal.symbol}")
        return None

    async def _process_buy_signal(self, signal: TradingSignal) -> BuyResponse | None:
        # Enhanced guard: check position status to prevent rapid reopening
        position_status = await self._get_position_status(signal.symbol, signal.source)

        if not position_status.can_open_new:
            if position_status.has_open_position:
                logger.info(f"Skipping buy for {signal.symbol}: open position already exists")
            elif position_status.recently_closed:
                logger.info(f"Skipping buy for {signal.symbol}: position was recently closed (cooling period)")
            return None

        # Валидация SL/TP для покупки
        if signal.stop_loss is None or signal.take_profit is None:
            logger.warning(f"Missing SL/TP for buy signal {signal.symbol}, using defaults")
            stop_loss = 2.0  # default 2%
            take_profit = 3.0  # default 3%
        else:
            stop_loss = signal.stop_loss
            take_profit = signal.take_profit

        logger.info(f"Processing buy signal for {signal.symbol}: SL={stop_loss:.2f}%, TP={take_profit:.2f}%")

        response = await self.client.buy(
            symbol=signal.symbol,
            usdt_amount=signal.amount,
            take_profit_percent=take_profit,
            stop_loss_percent=stop_loss,
        )
        logger.info(f"Buy signal processed for {signal.symbol}; order id: {response.order_id}")
        await self.uow_session.deals.create_from_buy(signal=signal, response=response)
        await self.uow_session.commit()
        return response

    async def _process_sell_signal(self, signal: TradingSignal) -> BuyResponse | None:
        # Guard: проверяем наличие открытой позиции для продажи
        open_position = await self.uow_session.deals.get_open_position(signal.symbol, signal.source)
        if not open_position:
            logger.info(f"Skipping sell signal for {signal.symbol}: no open position to close")
            return None

        logger.info(f"Found open position for {signal.symbol}: qty={open_position.qty}, price={open_position.price}")

        try:
            # Закрываем позицию по рынку, продавая всё количество
            qty_to_sell = Decimal(str(open_position.qty)) if open_position.qty is not None else None

            if qty_to_sell is None or qty_to_sell <= 0:
                logger.error(f"Invalid quantity to sell for {signal.symbol}: {qty_to_sell}")
                return None

            logger.info(f"Closing position for {signal.symbol}: selling {qty_to_sell} units")

            response = await self.client.sell(
                symbol=signal.symbol,
                qty=qty_to_sell,  # Продаем всё количество из открытой позиции
            )

            logger.info(
                f"Sell order executed for {signal.symbol}; order id: {response.order_id}, price: {response.price}"
            )

            # Создаем запись о закрытии позиции и помечаем исходную позицию как закрытую
            await self.uow_session.deals.close_position(signal=signal, response=response)
            await self.uow_session.commit()

            logger.info(f"Position successfully closed for {signal.symbol}")
            return response

        except Exception as e:
            logger.error(f"Failed to process sell signal for {signal.symbol}: {e}")
            # Откатываем транзакцию в случае ошибки
            try:
                await self.uow_session.rollback()
            except Exception as rollback_error:
                logger.error(f"Failed to rollback transaction: {rollback_error}")
            return None

    async def _get_position_status(self, symbol: str, source: str) -> PositionStatus:
        """Get comprehensive status of positions for a symbol and source."""
        # Get open position
        open_position = await self.uow_session.deals.get_open_position(symbol, source)

        # Check for recent closes
        recently_closed = await self.uow_session.deals.has_recently_closed_position(symbol, source, minutes=60)

        return PositionStatus(
            has_open_position=open_position is not None,
            open_position=open_position,
            recently_closed=recently_closed,
            can_open_new=open_position is None and not recently_closed,
        )
