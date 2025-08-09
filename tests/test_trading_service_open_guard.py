from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.consumer.services.trading import TradingService
from src.consumer.uow import UnitOfWork
from src.core.clients.bybit_async import BybitAsyncClient
from src.core.dto import TradingSignal
from src.core.enums import ActionEnum
from src.models import Deal


@pytest.mark.asyncio
async def test_skips_buy_when_open_deal_same_source(
    monkeypatch: pytest.MonkeyPatch,
    async_session_factory: async_sessionmaker[AsyncSession],
    uow: UnitOfWork,
) -> None:
    # Arrange: pre-insert an open BUY deal for the same symbol and source
    async with async_session_factory() as s:
        async with s.begin():
            s.add(
                Deal(
                    symbol="BTCUSDT",
                    action=ActionEnum.BUY,
                    qty=Decimal("50"),
                    price=100.0,
                    take_profit_price=102.0,
                    stop_loss_price=99.0,
                    # open position flags default to False
                    source="trand",
                )
            )

    # Client should not be called when open deal exists
    client = AsyncMock(spec=BybitAsyncClient)

    service = TradingService(client=client, uow=uow)
    signal = TradingSignal(
        symbol="BTCUSDT",
        amount=Decimal("50"),
        take_profit=2,
        stop_loss=1,
        action=ActionEnum.BUY,
        source="trand",
    )

    # Act
    response = await service.process_signal(signal)

    # Assert: no new deal created and response is None
    assert response is None
    assert client.buy.call_count == 0

    async with async_session_factory() as s:
        result = await s.execute(select(Deal))
        deals = result.scalars().all()

    assert len(deals) == 1
    assert deals[0].symbol == "BTCUSDT"
    assert deals[0].source == "trand"
