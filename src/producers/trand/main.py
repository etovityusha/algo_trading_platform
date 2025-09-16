import asyncio
import logging

from dishka.async_container import make_async_container

from di.config import ProducerConfigProvider
from di.exchange import ExchangeProvider, HttpClientProvider
from di.producer_service import ProducerServiceProvider
from logger import init_logging
from producers.trand.config.settings import TrandSettings
from producers.trand.services.producer_service import ProducerService

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
            await producer_service.run()
        finally:
            # Cleanup is handled by dishka container
            pass


if __name__ == "__main__":
    asyncio.run(main())
