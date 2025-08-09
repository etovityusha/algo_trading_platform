from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.consumer.services.trading import TradingService
from src.consumer.uow import UnitOfWork
from src.core.clients.bybit_async import BybitStubWriteClient
from src.core.dto import TradingSignal
from src.core.enums import ActionEnum
from src.models import Deal


@pytest.mark.asyncio
async def test_trading_service_persists_deal(
    monkeypatch: pytest.MonkeyPatch,
    async_session_factory: async_sessionmaker[AsyncSession],
    uow: UnitOfWork,
) -> None:
    async def fake_get_ticker_price(symbol: str) -> Decimal:
        return Decimal("100")

    client = BybitStubWriteClient(api_key="k", api_secret="s", is_demo=True)
    monkeypatch.setattr(client, "get_ticker_price", fake_get_ticker_price)

    service = TradingService(client=client, uow=uow)

    signal = TradingSignal(
        symbol="BTCUSDT",
        amount=Decimal("50"),
        take_profit=2,
        stop_loss=1,
        action=ActionEnum.BUY,
        source="itest",
    )

    # Act
    response = await service.process_signal(signal)

    # Assert response shape
    assert response is not None
    assert response.symbol == "BTCUSDT"
    assert response.price == Decimal("100")

    # Assert DB persisted deal
    async with async_session_factory() as s:
        result = await s.execute(select(Deal))
        deals = result.scalars().all()

    assert len(deals) == 1
    deal = deals[0]
    assert deal.external_id is not None
    assert deal.symbol == "BTCUSDT"
    assert deal.qty is not None
    # deal.qty is SQLAlchemy Numeric; convert via str to satisfy mypy
    assert Decimal(str(deal.qty)) == Decimal("50")
    assert deal.price == 100.0
    assert deal.take_profit_price == 102.0
    assert deal.stop_loss_price == 99.0
    assert deal.action == ActionEnum.BUY
    assert deal.source == "itest"
