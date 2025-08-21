import asyncio
import logging

from dishka.async_container import make_async_container

from src.di.config import ProducerConfigProvider
from src.di.exchange import ExchangeProvider, HttpClientProvider
from src.di.producer_service import ProducerServiceProvider
from src.logger import init_logging
from src.producers.trand.config.settings import TrandSettings
from src.producers.trand.services.producer_service import ProducerService

logger = logging.getLogger(__name__)


async def main() -> None:
    init_logging()

    settings = TrandSettings()
    container = make_async_container(
        ProducerConfigProvider(),
        HttpClientProvider(),
        ExchangeProvider(),
        ProducerServiceProvider(),
        context={TrandSettings: settings},
    )

    async with container() as request_container:
        producer_service = await request_container.get(ProducerService)
        try:
            await producer_service.run(interval_seconds=600)
        finally:
            # Cleanup is handled by dishka container
            pass


if __name__ == "__main__":
    asyncio.run(main())
