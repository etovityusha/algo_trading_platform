from collections.abc import AsyncIterator

import aiohttp
from dishka import Scope
from dishka.provider import Provider, provide

from configs import BybitSettings
from core.clients.bybit_async import BybitAsyncClient
from core.clients.interface import AbstractReadOnlyClient, AbstractWriteClient


class HttpClientProvider(Provider):
    @provide(scope=Scope.APP, provides=aiohttp.ClientSession)
    async def create_http_session(self) -> AsyncIterator[aiohttp.ClientSession]:
        session = aiohttp.ClientSession()
        yield session
        if not session.closed:
            await session.close()


class ExchangeProvider(Provider):
    @provide(scope=Scope.APP)
    async def create_write_client(
        self,
        cfg: BybitSettings,
        session: aiohttp.ClientSession,
    ) -> AsyncIterator[AbstractWriteClient]:
        client = BybitAsyncClient(
            api_key=cfg.API_KEY,
            api_secret=cfg.API_SECRET,
            is_demo=cfg.IS_DEMO,
            session=session,
        )
        yield client
        await client.close()

    @provide(scope=Scope.APP)
    async def create_read_client(
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


class ConsumerExchangeProvider(Provider):
    @provide(scope=Scope.REQUEST)
    async def create_write_client(
        self,
        cfg: BybitSettings,
        session: aiohttp.ClientSession,
    ) -> AbstractWriteClient:
        return BybitAsyncClient(
            api_key=cfg.API_KEY,
            api_secret=cfg.API_SECRET,
            is_demo=cfg.IS_DEMO,
            session=session,
        )

    @provide(scope=Scope.REQUEST)
    async def create_read_client(
        self,
        cfg: BybitSettings,
        session: aiohttp.ClientSession,
    ) -> AbstractReadOnlyClient:
        return BybitAsyncClient(
            api_key=cfg.API_KEY,
            api_secret=cfg.API_SECRET,
            is_demo=cfg.IS_DEMO,
            session=session,
        )
