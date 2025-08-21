from dishka import Scope
from dishka.provider import Provider, provide

from src.configs import BybitSettings
from src.core.clients.bybit_async import BybitAsyncClient
from src.core.clients.interface import AbstractReadOnlyClient


class ProducerExchangeProvider(Provider):
    @provide(scope=Scope.APP)
    async def create_read_only_client(
        self,
        cfg: BybitSettings,
    ) -> AbstractReadOnlyClient:
        return BybitAsyncClient(
            api_key=cfg.API_KEY,
            api_secret=cfg.API_SECRET,
            is_demo=cfg.IS_DEMO,
        )
