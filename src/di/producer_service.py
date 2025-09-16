from dishka import Provider, Scope, provide
from faststream.rabbit import QueueType, RabbitBroker, RabbitQueue

from configs import RabbitSettings
from core.clients.interface import AbstractReadOnlyClient
from producers.trand.services.producer_service import ProducerService
from producers.trand.strategy import TrandStrategy


class ProducerServiceProvider(Provider):
    @provide(scope=Scope.APP)
    async def create_broker(self, rabbit_config: RabbitSettings) -> RabbitBroker:
        broker = RabbitBroker(rabbit_config.dsn)
        await broker.connect()
        return broker

    @provide(scope=Scope.APP)
    def create_trading_queue(self) -> RabbitQueue:
        return RabbitQueue("trading_signals", durable=True, queue_type=QueueType.CLASSIC)

    @provide(scope=Scope.REQUEST)
    def create_trand_strategy(self, client: AbstractReadOnlyClient) -> TrandStrategy:
        return TrandStrategy(client=client)

    @provide(scope=Scope.REQUEST)
    def create_producer_service(
        self,
        strategy: TrandStrategy,
        broker: RabbitBroker,
        queue: RabbitQueue,
        tickers: list[str],
    ) -> ProducerService:
        return ProducerService(
            strategy=strategy,
            broker=broker,
            queue=queue,
            tickers=tickers,
        )
