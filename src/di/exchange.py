from dishka import Scope
from dishka.provider import Provider, provide

from src.configs import BybitSettings
from src.core.clients.bybit_async import BybitAsyncClient
from src.core.clients.interface import AbstractReadOnlyClient, AbstractWriteClient


class ExchangeProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def create_write_client(
        self,
        cfg: BybitSettings,
    ) -> AbstractWriteClient:
        return BybitAsyncClient(
            api_key=cfg.API_KEY,
            api_secret=cfg.API_SECRET,
            is_demo=cfg.IS_DEMO,
        )

    @provide(scope=Scope.REQUEST)
    async def create_read_client(
        self,
        cfg: BybitSettings,
    ) -> AbstractReadOnlyClient:
        return BybitAsyncClient(
            api_key=cfg.API_KEY,
            api_secret=cfg.API_SECRET,
            is_demo=cfg.IS_DEMO,
        )
