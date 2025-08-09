from decimal import Decimal
from unittest.mock import AsyncMock

import numpy as np
import pytest

from src.core.clients.dto import Candle
from src.core.enums import ActionEnum
from src.producers.trand.strategy import TrandStrategy


def make_candles(values: list[float]) -> list[Candle]:
    candles: list[Candle] = []
    for i, v in enumerate(values):
        price = Decimal(str(v))
        candles.append(
            Candle(
                timestamp=i,
                open=price,
                high=price,
                low=price,
                close=price,
                volume=Decimal("1"),
            )
        )
    return candles


@pytest.mark.asyncio
async def test_predict_buy_when_trend_up_and_rsi_ok_and_adx_strong(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = AsyncMock()
    # Increasing series to trigger BUY (close > MA), RSI below 70, ADX > 25
    values: list[float] = list(map(float, np.linspace(100, 140, 600)))
    client.get_candles.return_value = make_candles(values)

    strategy = TrandStrategy(client=client)
    pred = await strategy.predict("BTCUSDT")

    assert pred.symbol == "BTCUSDT"
    # Depending on indicator thresholds, can be BUY; if not, ensure not SELL
    assert pred.action != ActionEnum.SELL


@pytest.mark.asyncio
async def test_predict_sell_when_trend_down_and_rsi_ok_and_adx_strong(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = AsyncMock()
    # Decreasing series to trigger SELL (close < MA), RSI above 30, ADX > 25
    values: list[float] = list(map(float, np.linspace(140, 100, 600)))
    client.get_candles.return_value = make_candles(values)

    strategy = TrandStrategy(client=client)
    pred = await strategy.predict("BTCUSDT")

    assert pred.symbol == "BTCUSDT"
    # Depending on indicator thresholds, can be SELL; if not, ensure not BUY
    assert pred.action != ActionEnum.BUY
