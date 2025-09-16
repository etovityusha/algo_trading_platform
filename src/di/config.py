from dishka import Provider, Scope, from_context, provide

from configs import BybitSettings, PostgresSettings, RabbitSettings
from consumer.config.settings import ConsumerSettings
from producers.trand.config.settings import TrandSettings


class ConsumerConfigProvider(Provider):
    scope = Scope.APP
    config = from_context(ConsumerSettings)

    @provide(scope=Scope.APP)
    def get_db_config(self, config: ConsumerSettings) -> PostgresSettings:
        return config.postgres

    @provide(scope=Scope.APP)
    def get_bybit_config(self, config: ConsumerSettings) -> BybitSettings:
        return config.bybit


class ProducerConfigProvider(Provider):
    scope = Scope.APP
    config = from_context(TrandSettings)

    @provide(scope=Scope.APP)
    def get_rabbit_config(self, config: TrandSettings) -> RabbitSettings:
        return config.rabbit

    @provide(scope=Scope.APP)
    def get_bybit_ro_config(self, config: TrandSettings) -> BybitSettings:
        return config.bybit_ro

    @provide(scope=Scope.APP)
    def get_tickers(self, config: TrandSettings) -> list[str]:
        return config.TICKERS
