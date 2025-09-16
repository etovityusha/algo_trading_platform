import asyncio
import logging
import time
from decimal import Decimal

from faststream.rabbit import RabbitBroker, RabbitQueue

from core.dto import TradingSignal
from producers.momentum.strategy import MomentumStrategy

logger = logging.getLogger(__name__)


class ProducerService:
    def __init__(
        self,
        strategy: MomentumStrategy,
        broker: RabbitBroker,
        queue: RabbitQueue,
        tickers: list[str],
    ) -> None:
        self.strategy = strategy
        self.broker = broker
        self.queue = queue
        self.tickers = tickers
        self.strategy_config = strategy.get_config()

    async def run(self) -> None:
        """Run the momentum producer with 5-minute intervals for aggressive trading."""
        logger.info(f"Starting momentum producer with {len(self.tickers)} tickers")
        try:
            while True:
                now = time.time()
                await self._process_all_tickers()
                sleep_time = (self.strategy_config.signal_interval_minutes * 60) - (time.time() - now)
                await asyncio.sleep(sleep_time)
        except Exception as e:
            logger.exception(f"Momentum producer error: {e}")
            raise

    async def _process_all_tickers(self) -> None:
        """Process all tickers and send trading signals."""
        for ticker in self.tickers:
            try:
                await self._process_ticker(ticker)
            except Exception as e:
                logger.error(f"Error processing ticker {ticker}: {e}")

    async def _process_ticker(self, ticker: str) -> None:
        """Process a single ticker and send trading signal if needed."""
        prediction = await self.strategy.predict(ticker)
        logger.info(f"Momentum prediction for {ticker}: {prediction.action}")

        # Агрессивная стратегия использует больший размер позиции
        message = TradingSignal(
            symbol=ticker,
            amount=Decimal("150"),  # Увеличенный размер для агрессивной стратегии
            take_profit=prediction.take_profit_percent,
            stop_loss=prediction.stop_loss_percent,
            action=prediction.action,
            source="momentum",
        )

        await self.broker.publish(message.model_dump(mode="json"), queue=self.queue)
        logger.info(f"Sent momentum trading signal for {ticker}: {prediction.action}")
