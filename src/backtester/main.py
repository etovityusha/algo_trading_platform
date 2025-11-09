import logging

from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitQueue
from faststream.rabbit.schemas import Channel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backtester.config.settings import BacktesterSettings
from backtester.repositories.backtest_repository import BacktestRepository
from backtester.schemas import BacktestMessage
from backtester.services.backtest_service import BacktestService
from core.clients.bybit_async import BybitAsyncClient
from logger import init_logging

logger = logging.getLogger(__name__)

# Глобальные объекты
settings: BacktesterSettings
async_session_factory: sessionmaker
engine = None


def _configure_app() -> tuple[FastStream, RabbitBroker]:
    global settings, async_session_factory, engine

    init_logging()

    settings = BacktesterSettings()

    # Создаем engine для базы данных
    engine = create_async_engine(
        settings.postgres.async_dsn,
        pool_pre_ping=True,
        connect_args={"server_settings": {"timezone": "UTC"}},
    )

    # Создаем фабрику сессий
    async_session_factory = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Configure broker with prefetch_count=1 to limit to 1 parallel task due to CPU usage
    broker = RabbitBroker(
        settings.rabbit.dsn,
        graceful_timeout=30.0,
        default_channel=Channel(prefetch_count=1),
    )
    app = FastStream(broker, logger=logger)

    @app.on_shutdown
    async def shutdown_handler():
        """Gracefully shutdown the application and cleanup resources"""
        logger.info("Shutting down backtester application...")
        if engine:
            await engine.dispose()
        logger.info("Application shutdown complete")

    return app, broker


app, broker = _configure_app()


@broker.subscriber(
    RabbitQueue(
        name="backtest_tasks",
        durable=True,
    )
)
async def process_backtest_message(message: BacktestMessage) -> None:
    """Process backtest request from RabbitMQ message.

    Parameters are received directly in the message, not from the database.
    Checks if result already exists before running backtest.

    Note: prefetch_count=1 ensures only 1 message is processed at a time per worker.
    For horizontal scaling, run multiple instances of this worker.
    """
    logger.info(
        f"Received backtest request: {message.symbol} | {message.strategy_name} | "
        f"{message.start_date.date()} to {message.end_date.date()}"
    )

    # Create Bybit client
    bybit_client = BybitAsyncClient(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        is_demo=settings.bybit_is_demo,
    )

    async with async_session_factory() as session:
        try:
            repository = BacktestRepository(session)
            backtest_service = BacktestService(repository, bybit_client)

            await backtest_service.process_backtest(message)

        except Exception as e:
            logger.error(f"Error processing backtest message: {e}", exc_info=True)
            raise
        finally:
            await bybit_client.close()
