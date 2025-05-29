import logging
import os
import asyncio
from decimal import Decimal

from faststream.rabbit import RabbitBroker, RabbitQueue

from dotenv import load_dotenv

from clients.bybit_async import BybitAsyncClient
from dto import TradingSignal
from enums import ActionEnum
from logger import init_logging
from strategies.trand import TrandStrategy

init_logging()
logger = logging.getLogger(__name__)
ticker_list = [
    "BTCUSDT",
    "ETHUSDT",
    "XRPUSDT",
]


async def main():
    load_dotenv()
    broker = RabbitBroker(
        f"amqp://{os.getenv('RABBITMQ_USER')}:{os.getenv('RABBITMQ_PASS')}@{os.getenv('RABBITMQ_HOST')}"
    )
    await broker.connect()
    trading_queue = RabbitQueue("trading_signals", durable=True)
    async with BybitAsyncClient(
        api_key=os.getenv("BYBIT_RO_API_KEY"),
        api_secret=os.getenv("BYBIT_RO_API_SECRET"),
        is_demo=os.getenv("BYBIT_RO_IS_DEMO", "true") == "true",
    ) as client:
        try:
            strategy = TrandStrategy(client=client)
            while True:
                for ticker in ticker_list:
                    prediction = await strategy.predict(ticker)
                    logger.info(f"Prediction for {ticker}: {prediction.action}")
                    if prediction.action == ActionEnum.BUY:
                        message = TradingSignal(
                            symbol=ticker,
                            amount=Decimal("100"),  # hardcore 100usdt
                            take_profit=2,
                            stop_loss=1,
                            action=prediction.action,
                        )
                        await broker.publish(message.model_dump(), queue=trading_queue)
                await asyncio.sleep(600)
        finally:
            await broker.close()


if __name__ == "__main__":
    asyncio.run(main())
