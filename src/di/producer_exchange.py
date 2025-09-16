from collections.abc import AsyncIterator

import aiohttp
from dishka import Scope
from dishka.provider import Provider, provide

from configs import BybitSettings
from core.clients.bybit_async import BybitAsyncClient
from core.clients.interface import AbstractReadOnlyClient


class ProducerHttpClientProvider(Provider):
    @provide(scope=Scope.APP, provides=aiohttp.ClientSession)
    async def create_http_session(self) -> AsyncIterator[aiohttp.ClientSession]:
        session = aiohttp.ClientSession()
        yield session
        if not session.closed:
            await session.close()


class ProducerExchangeProvider(Provider):
    @provide(scope=Scope.APP)
    async def create_read_only_client(
        self,
        cfg: BybitSettings,
        session: aiohttp.ClientSession,
    ) -> AsyncIterator[AbstractReadOnlyClient]:
        client = BybitAsyncClient(
            api_key=cfg.API_KEY,
            api_secret=cfg.API_SECRET,
            is_demo=cfg.IS_DEMO,
            session=session,
        )
        yield client
        await client.close()
