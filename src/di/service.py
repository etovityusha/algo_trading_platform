from dishka import Provider, Scope, provide

from consumer.services.position_manager import PositionManagerService
from consumer.services.trading import TradingService
from consumer.uow import UnitOfWork, UoWSession
from core.clients.interface import AbstractReadOnlyClient, AbstractWriteClient


class ServiceProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_trading_service(self, write_client: AbstractWriteClient, uow_session: UoWSession) -> TradingService:
        return TradingService(client=write_client, uow_session=uow_session)

    @provide(scope=Scope.REQUEST)
    def get_position_manager_service(
        self, read_client: AbstractReadOnlyClient, uow: UnitOfWork
    ) -> PositionManagerService:
        return PositionManagerService(uow, read_client)
