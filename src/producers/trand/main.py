import asyncio
import logging
from decimal import Decimal

from faststream.rabbit import RabbitBroker, RabbitQueue

from src.core.clients.bybit_async import BybitAsyncClient
from src.core.dto import TradingSignal
from src.logger import init_logging
from src.producers.trand.config.settings import TrandSettings
from src.producers.trand.strategy import TrandStrategy

logger = logging.getLogger(__name__)


async def main() -> None:
    init_logging()
    settings = TrandSettings()
    broker = RabbitBroker(
        f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASS}@{settings.RABBITMQ_HOST}"
    )
    await broker.connect()
    async with BybitAsyncClient(
        api_key=settings.BYBIT_RO_API_KEY,
        api_secret=settings.BYBIT_RO_API_SECRET,
        is_demo=settings.BYBIT_RO_IS_DEMO,
    ) as client:
        strategy = TrandStrategy(client=client)
        trading_queue = RabbitQueue("trading_signals", durable=True)
        try:
            while True:
                for ticker in settings.TICKERS:
                    prediction = await strategy.predict(ticker)
                    logger.info(f"Prediction for {ticker}: {prediction.action}")
                    message = TradingSignal(
                        symbol=ticker,
                        amount=Decimal("100"),
                        take_profit=2,
                        stop_loss=1,
                        action=prediction.action,
                        source="trand",
                    )
                    await broker.publish(message.model_dump(), queue=trading_queue)
                    logger.info(f"Sent trading signal for {ticker}")
                await asyncio.sleep(600)
        finally:
            await broker.close()


if __name__ == "__main__":
    asyncio.run(main())
