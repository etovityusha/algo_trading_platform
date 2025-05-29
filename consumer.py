import os
import logging
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Optional

from faststream import FastStream, Logger
from faststream.rabbit import RabbitBroker, RabbitQueue, QueueType
from pydantic import BaseModel
from dotenv import load_dotenv

from clients.bybit_async import BybitAsyncClient
from clients.dto import BuyResponse
from enums import ActionEnum
from logger import init_logging

init_logging()
logger = logging.getLogger(__name__)

load_dotenv()


class TradingSignal(BaseModel):
    symbol: str
    amount: Decimal
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    action: ActionEnum = ActionEnum.BUY


# Создание брокера RabbitMQ
broker = RabbitBroker(
    host=os.getenv("RABBITMQ_HOST"),
    url=f"amqp://{os.getenv('RABBITMQ_USER')}:{os.getenv('RABBITMQ_PASS')}@localhost:5672/",
)


@asynccontextmanager
async def lifespan():
    # Инициализация клиента перед запуском приложения
    global bybit_client
    bybit_client = BybitAsyncClient(
        api_key=os.getenv("BYBIT_API_KEY"),
        api_secret=os.getenv("BYBIT_API_SECRET"),
        is_demo=os.getenv("BYBIT_IS_DEMO", "true") == "true",
    )
    await bybit_client.__aenter__()

    try:
        yield
    finally:
        await bybit_client.__aexit__(None, None, None)


app = FastStream(broker, logger=Logger(logger), lifespan=lifespan)
queue = RabbitQueue(
    name="trading_signals",
    durable=True,
    queue_type=QueueType.CLASSIC,
)


@broker.subscriber(queue)
async def process_trading_signal(signal: TradingSignal) -> None:
    logger.info(f"Получен сигнал: {signal}")
    if signal.action != ActionEnum.BUY:
        logger.info(f"Не реализована обработка сигнала {signal.action}")
        return
    response: BuyResponse = await bybit_client.buy(
        symbol=signal.symbol,
        usdt_amount=signal.amount,
        take_profit_percent=signal.take_profit,
        stop_loss_percent=signal.stop_loss,
    )
    logger.info(
        f"Ордер выполнен. Куплено: {response.symbol}  {response.qty}*{response.price}"
    )
