import logging

from faststream import FastStream, Logger
from faststream.rabbit import RabbitQueue, QueueType, RabbitBroker

from src.core.dto import TradingSignal
from src.logger import init_logging
from src.consumer.config.settings import ConsumerSettings
from src.consumer.services.trading import TradingService
from src.core.clients.bybit_async import BybitAsyncClient

logger = logging.getLogger(__name__)

init_logging()
settings = ConsumerSettings()
broker = RabbitBroker(
    f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASS}@{settings.RABBITMQ_HOST}"
)
app = FastStream(logger=Logger(logger), broker=broker)

queue = RabbitQueue(
    name="trading_signals",
    durable=True,
    queue_type=QueueType.CLASSIC,
)


@broker.subscriber(queue)
async def process_trading_signal(signal: TradingSignal) -> None:
    async with BybitAsyncClient(
        api_key=settings.BYBIT_API_KEY,
        api_secret=settings.BYBIT_API_SECRET,
        is_demo=settings.BYBIT_IS_DEMO,
    ) as client:
        trading_service = TradingService(client=client)
        await trading_service.process_signal(signal)


if __name__ == "__main__":
    app.run()
