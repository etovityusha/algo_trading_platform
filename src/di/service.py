from dishka import Provider, Scope, provide

from src.consumer.services.position_manager import PositionManagerService
from src.consumer.services.trading import TradingService
from src.consumer.uow import UoWSession
from src.core.clients.interface import AbstractReadOnlyClient, AbstractWriteClient


class ServiceProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_trading_service(self, write_client: AbstractWriteClient, uow_session: UoWSession) -> TradingService:
        return TradingService(client=write_client, uow_session=uow_session)

    @provide(scope=Scope.REQUEST)
    def get_position_manager_service(
        self, read_client: AbstractReadOnlyClient, uow_session: UoWSession
    ) -> PositionManagerService:
        return PositionManagerService(uow_session=uow_session, read_client=read_client)
