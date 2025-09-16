import asyncio
import logging
import time
from decimal import Decimal

from faststream.rabbit import RabbitBroker, RabbitQueue

from core.dto import TradingSignal
from producers.trand.strategy import TrandStrategy

logger = logging.getLogger(__name__)


class ProducerService:
    def __init__(
        self,
        strategy: TrandStrategy,
        broker: RabbitBroker,
        queue: RabbitQueue,
        tickers: list[str],
    ) -> None:
        self.strategy = strategy
        self.strategy_config = strategy.get_config()
        self.broker = broker
        self.queue = queue
        self.tickers = tickers

    async def run(self, interval_seconds: int = 600) -> None:
        """Run the producer in an infinite loop."""
        logger.info(f"Starting producer with {len(self.tickers)} tickers")
        try:
            while True:
                now = time.time()
                await self._process_all_tickers()
                sleep_time = (self.strategy_config.signal_interval_minutes * 60) - (time.time() - now)
                await asyncio.sleep(sleep_time)
        except Exception as e:
            logger.exception(f"Producer error: {e}")
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
        logger.info(f"Prediction for {ticker}: {prediction.action}")

        message = TradingSignal(
            symbol=ticker,
            amount=Decimal("100"),
            take_profit=prediction.take_profit_percent,
            stop_loss=prediction.stop_loss_percent,
            action=prediction.action,
            source="trand",
        )

        await self.broker.publish(message.model_dump(mode="json"), queue=self.queue)
        logger.info(f"Sent trading signal for {ticker}")
