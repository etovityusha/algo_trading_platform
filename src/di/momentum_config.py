from dishka import Provider, Scope, from_context, provide

from src.configs import BybitSettings, RabbitSettings
from src.producers.momentum.config.settings import MomentumSettings


class MomentumConfigProvider(Provider):
    scope = Scope.APP
    config = from_context(MomentumSettings)

    @provide(scope=Scope.APP)
    def get_rabbit_config(self, config: MomentumSettings) -> RabbitSettings:
        return config.rabbit

    @provide(scope=Scope.APP)
    def get_bybit_ro_config(self, config: MomentumSettings) -> BybitSettings:
        return config.bybit_ro

    @provide(scope=Scope.APP)
    def get_tickers(self, config: MomentumSettings) -> list[str]:
        return config.TICKERS
