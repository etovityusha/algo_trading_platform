import logging

from faststream import FastStream
from faststream.rabbit import QueueType, RabbitBroker, RabbitQueue

from src.consumer.config.settings import ConsumerSettings
from src.consumer.db import get_session_factory
from src.consumer.services.trading import TradingService
from src.consumer.uow import UnitOfWork
from src.core.clients.bybit_async import BybitAsyncClient
from src.core.dto import TradingSignal
from src.logger import init_logging

logger = logging.getLogger(__name__)

init_logging()
settings = ConsumerSettings()
broker = RabbitBroker(
    f"amqp://{settings.rabbit.USER}:{settings.rabbit.PASS}@{settings.rabbit.HOST}:{settings.rabbit.PORT}"
)
app = FastStream(logger=logger, broker=broker)

queue = RabbitQueue(
    name="trading_signals",
    durable=True,
    queue_type=QueueType.CLASSIC,
)


@broker.subscriber(queue)
async def process_trading_signal(signal: TradingSignal) -> None:
    async with BybitAsyncClient(
        api_key=settings.bybit.API_KEY,
        api_secret=settings.bybit.API_SECRET,
        is_demo=settings.bybit.IS_DEMO,
    ) as client:
        uow = UnitOfWork(session_factory=get_session_factory())
        trading_service = TradingService(client=client, uow=uow)
        await trading_service.process_signal(signal)
