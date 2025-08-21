from dishka import Provider, Scope, provide

from src.consumer.services.trading import TradingService
from src.consumer.uow import UoWSession
from src.core.clients.interface import AbstractWriteClient


class ServiceProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_trading_service(self, write_client: AbstractWriteClient, uow_session: UoWSession) -> TradingService:
        return TradingService(client=write_client, uow_session=uow_session)
