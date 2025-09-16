import logging

from dishka.async_container import make_async_container
from dishka.entities.depends_marker import FromDishka
from dishka.integrations import faststream as faststream_integration
from faststream import FastStream
from faststream.rabbit import QueueType, RabbitBroker, RabbitQueue

from consumer.config.settings import ConsumerSettings
from consumer.services.position_manager import PositionManagerService
from consumer.services.trading import TradingService
from core.dto import TradingSignal
from di.config import ConsumerConfigProvider
from di.database import DatabaseProvider
from di.exchange import ConsumerExchangeProvider, HttpClientProvider
from di.service import ServiceProvider
from logger import init_logging

logger = logging.getLogger(__name__)


def _configure_app() -> tuple[FastStream, RabbitBroker]:
    init_logging()

    settings = ConsumerSettings()
    container = make_async_container(
        ConsumerConfigProvider(),
        DatabaseProvider(),
        HttpClientProvider(),
        ConsumerExchangeProvider(),
        ServiceProvider(),
        context={ConsumerSettings: settings},
    )
    broker = RabbitBroker(settings.rabbit.dsn)
    app = FastStream(logger=logger, broker=broker)
    faststream_integration.setup_dishka(container=container, app=app, auto_inject=True)

    @app.on_shutdown
    async def shutdown_handler():
        """Gracefully shutdown the application and cleanup resources"""
        logger.info("Shutting down consumer application...")
        await container.close()
        logger.info("Application shutdown complete")

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
async def handle_open_positions(
    position_manager: FromDishka[PositionManagerService],
) -> None:
    await position_manager.handle_open_positions()
