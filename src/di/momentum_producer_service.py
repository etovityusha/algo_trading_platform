from dishka import Provider, Scope, provide
from faststream.rabbit import QueueType, RabbitBroker, RabbitQueue

from configs import RabbitSettings
from core.clients.interface import AbstractReadOnlyClient
from producers.momentum.services.producer_service import ProducerService
from producers.momentum.strategy import MomentumStrategy


class MomentumProducerServiceProvider(Provider):
    @provide(scope=Scope.APP)
    async def create_broker(self, rabbit_config: RabbitSettings) -> RabbitBroker:
        broker = RabbitBroker(rabbit_config.dsn)
        await broker.connect()
        return broker

    @provide(scope=Scope.APP)
    def create_trading_queue(self) -> RabbitQueue:
        return RabbitQueue("trading_signals", durable=True, queue_type=QueueType.CLASSIC)

    @provide(scope=Scope.REQUEST)
    def create_momentum_strategy(self, client: AbstractReadOnlyClient) -> MomentumStrategy:
        return MomentumStrategy(client=client)

    @provide(scope=Scope.REQUEST)
    def create_producer_service(
        self,
        strategy: MomentumStrategy,
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
