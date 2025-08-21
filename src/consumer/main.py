import logging

from dishka.async_container import make_async_container
from dishka.entities.depends_marker import FromDishka
from dishka.integrations import faststream as faststream_integration
from faststream import FastStream
from faststream.rabbit import QueueType, RabbitBroker, RabbitQueue

from src.consumer.config.settings import ConsumerSettings
from src.consumer.services.trading import TradingService
from src.core.clients.interface import AbstractWriteClient
from src.core.dto import TradingSignal
from src.di.config import ConsumerConfigProvider
from src.di.database import DatabaseProvider
from src.di.exchange import ExchangeProvider
from src.di.service import ServiceProvider
from src.logger import init_logging

logger = logging.getLogger(__name__)


def _configure_app() -> tuple[FastStream, RabbitBroker]:
    init_logging()

    settings = ConsumerSettings()
    container = make_async_container(
        ConsumerConfigProvider(),
        DatabaseProvider(),
        ExchangeProvider(),
        ServiceProvider(),
        context={ConsumerSettings: settings},
    )
    broker = RabbitBroker(settings.rabbit.dsn)
    app = FastStream(logger=logger, broker=broker)
    faststream_integration.setup_dishka(container=container, app=app, auto_inject=True)
    return app, broker


app, broker = _configure_app()


@broker.subscriber(
    RabbitQueue(
        name="trading_signals",
        durable=True,
        queue_type=QueueType.CLASSIC,
    )
)
async def process_trading_signal(
    signal: TradingSignal,
    trading_service: FromDishka[TradingService],
) -> None:
    logger.info(f"Processing trading signal: {signal.symbol} {signal.action}")
    await trading_service.process_signal(signal)


@broker.subscriber(
    RabbitQueue(
        name="handle_open_positions",
        durable=True,
        queue_type=QueueType.CLASSIC,
    )
)
async def handle_open_positions(client: FromDishka[AbstractWriteClient]) -> None:
    logger.info(f"handle_positions_queue task stub, {client=}")
