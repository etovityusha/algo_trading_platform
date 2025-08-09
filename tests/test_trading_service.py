from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.consumer.services.trading import TradingService
from src.core.clients.bybit_async import BybitAsyncClient
from src.core.clients.dto import BuyResponse
from src.core.dto import TradingSignal
from src.core.enums import ActionEnum


@pytest.mark.asyncio
async def test_process_signal_non_buy_returns_none_and_no_buy_called() -> None:
    client = AsyncMock(spec=BybitAsyncClient)
    service = TradingService(client=client)

    signal = TradingSignal(
        symbol="BTCUSDT",
        amount=Decimal("100"),
        take_profit=2,
        stop_loss=1,
        action=ActionEnum.SELL,
        source="unit",
    )

    result = await service.process_signal(signal)

    assert result is None
    client.buy.assert_not_called()


@pytest.mark.asyncio
async def test_process_signal_buy_calls_client_and_returns_response() -> None:
    client = AsyncMock(spec=BybitAsyncClient)
    expected_response = BuyResponse(
        order_id="order-1",
        symbol="BTCUSDT",
        qty=Decimal("1.0"),
        price=Decimal("100"),
        stop_loss_price=Decimal("99.00"),
        take_profit_price=Decimal("102.00"),
    )
    client.buy.return_value = expected_response

    service = TradingService(client=client)

    signal = TradingSignal(
        symbol="BTCUSDT",
        amount=Decimal("100"),
        take_profit=2,
        stop_loss=1,
        action=ActionEnum.BUY,
        source="unit",
    )

    result = await service.process_signal(signal)

    client.buy.assert_awaited_once()
    client.buy.assert_awaited_once_with(
        symbol="BTCUSDT",
        usdt_amount=Decimal("100"),
        take_profit_percent=2,
        stop_loss_percent=1,
    )
    assert result == expected_response
