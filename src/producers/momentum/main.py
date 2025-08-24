import asyncio
import logging

from dishka.async_container import make_async_container

from src.di.exchange import ExchangeProvider, HttpClientProvider
from src.di.momentum_config import MomentumConfigProvider
from src.di.momentum_producer_service import MomentumProducerServiceProvider
from src.logger import init_logging
from src.producers.momentum.config.settings import MomentumSettings
from src.producers.momentum.services.producer_service import ProducerService

logger = logging.getLogger(__name__)


async def main() -> None:
    init_logging()

    settings = MomentumSettings()
    container = make_async_container(
        MomentumConfigProvider(),
        HttpClientProvider(),
        ExchangeProvider(),
        MomentumProducerServiceProvider(),
        context={MomentumSettings: settings},
    )

    async with container() as request_container:
        producer_service = await request_container.get(ProducerService)
        try:
            # Запуск с интервалом 5 минут для агрессивной торговли
            await producer_service.run()
        finally:
            # Cleanup is handled by dishka container
            pass


if __name__ == "__main__":
    asyncio.run(main())
