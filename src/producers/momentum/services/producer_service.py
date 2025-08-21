import asyncio
import logging
from decimal import Decimal

from faststream.rabbit import RabbitBroker, RabbitQueue

from src.core.dto import TradingSignal
from src.producers.momentum.strategy import MomentumStrategy

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

    async def run(self, interval_seconds: int = 300) -> None:
        """Run the momentum producer with 5-minute intervals for aggressive trading."""
        logger.info(f"Starting momentum producer with {len(self.tickers)} tickers")
        try:
            while True:
                await self._process_all_tickers()
                logger.info(f"Sleeping for {interval_seconds} seconds")
                await asyncio.sleep(interval_seconds)
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
            take_profit=prediction.take_profit,
            stop_loss=prediction.stop_loss,
            action=prediction.action,
            source="momentum",
        )

        await self.broker.publish(message.model_dump(mode="json"), queue=self.queue)
        logger.info(f"Sent momentum trading signal for {ticker}: {prediction.action}")
