import datetime as dt
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.consumer.services.statistics import StatisticsService, DealStats
from src.core.clients.dto import Candle
from src.core.clients.interface import AbstractReadOnlyClient
from src.core.enums import ActionEnum
from src.models import Deal


class StubReadOnlyClient(AbstractReadOnlyClient):
    def __init__(self, candles_by_symbol: dict[str, list[Candle]]):
        self._candles_by_symbol = candles_by_symbol

    async def get_candles(self, symbol: str, interval: str = "15", limit: int = 200) -> list[Candle]:
        # Return at most last `limit` candles
        candles = self._candles_by_symbol.get(symbol, [])
        return candles[-limit:]

    async def get_instrument_info(self, symbol: str) -> dict:
        return {}

    async def get_ticker_price(self, symbol: str) -> Decimal:
        candles = self._candles_by_symbol.get(symbol, [])
        return Decimal(str(candles[-1].close if candles else 0))


def ms(ts: dt.datetime) -> int:
    return int(ts.timestamp() * 1000)


@pytest.mark.asyncio
async def test_statistics_service_closes_in_period_and_in_next_week(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    symbol = "BTCUSDT"

    # Build time window: end is yesterday, start is 2 days ago
    now = dt.datetime.now(tz=dt.timezone.utc)
    start = now - dt.timedelta(days=2)
    end = now - dt.timedelta(days=1)

    # Create two deals:
    # - deal_tp closes via TP inside [start, end)
    # - deal_sl closes via SL within the next week (but before now)
    deal_tp_created = start + dt.timedelta(hours=3)
    deal_sl_created = start + dt.timedelta(hours=6)

    entry = 100.0
    qty_usdt = Decimal("50")

    async with async_session_factory() as s:
        async with s.begin():
            s.add(
                Deal(
                    created_at=deal_tp_created,
                    external_id=None,
                    symbol=symbol,
                    qty=qty_usdt,
                    price=entry,
                    take_profit_price=105.0,
                    stop_loss_price=95.0,
                    action=ActionEnum.BUY,
                    source="itest",
                )
            )
            s.add(
                Deal(
                    created_at=deal_sl_created,
                    external_id=None,
                    symbol=symbol,
                    qty=qty_usdt,
                    price=entry,
                    take_profit_price=110.0,
                    stop_loss_price=90.0,
                    action=ActionEnum.BUY,
                    source="itest",
                )
            )

    # Build candles: include some before and after deals
    candles: list[Candle] = [
        Candle(open=Decimal("100"), high=Decimal("101"), low=Decimal("99"), close=Decimal("100"), volume=Decimal("1"), timestamp=ms(start + dt.timedelta(hours=1))),
        # After deal_tp, within period: reach TP=105
        Candle(open=Decimal("100"), high=Decimal("106"), low=Decimal("99"), close=Decimal("105"), volume=Decimal("1"), timestamp=ms(start + dt.timedelta(hours=10))),
        # After deal_sl, but still within [start, end): no hit
        Candle(open=Decimal("103"), high=Decimal("104"), low=Decimal("98"), close=Decimal("100"), volume=Decimal("1"), timestamp=ms(start + dt.timedelta(hours=20))),
        # After end, but within next week: hit SL=90 for deal_sl
        Candle(open=Decimal("100"), high=Decimal("101"), low=Decimal("89"), close=Decimal("90"), volume=Decimal("1"), timestamp=ms(now - dt.timedelta(hours=12))),
    ]

    client = StubReadOnlyClient({symbol: candles})
    service = StatisticsService(session_factory=async_session_factory, client=client, candles_interval="15")

    stats: DealStats = await service.compute(start_inclusive=start, end_exclusive=end, symbol=symbol, source="itest")

    assert stats.count == 2
    assert stats.take_profit_triggered == 1
    assert stats.stop_loss_triggered == 1

    # total invested is sum of qty in USDT per our model
    assert stats.total_invested_usd == pytest.approx(100.0)

    # Totals & counts
    # PnL: TP +5% on 50 USDT -> +2.5; SL -10% on 50 USDT -> -5.0; total -2.5
    assert stats.total_earned_usd == pytest.approx(-2.5, rel=1e-6)
    assert stats.winning_deals == 1
    assert stats.losing_deals == 1
    assert len(stats.usd_diffs) == 2
    # Diffs contain +2.5 and -5.0
    assert sorted(stats.usd_diffs) == pytest.approx(sorted([2.5, -5.0]))


@pytest.mark.asyncio
async def test_statistics_service_ignores_open_deal_without_levels(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    symbol = "BTCUSDT"
    now = dt.datetime.now(tz=dt.timezone.utc)
    start = now - dt.timedelta(days=2)
    end = now - dt.timedelta(days=1)

    # Open deal without TP/SL
    async with async_session_factory() as s:
        async with s.begin():
            s.add(
                Deal(
                    created_at=start + dt.timedelta(hours=2),
                    external_id=None,
                    symbol=symbol,
                    qty=Decimal("30"),
                    price=100.0,
                    take_profit_price=None,
                    stop_loss_price=None,
                    action=ActionEnum.BUY,
                    source="itest",
                )
            )

    # Candles do not matter; there are no levels
    client = StubReadOnlyClient({symbol: []})
    service = StatisticsService(session_factory=async_session_factory, client=client, candles_interval="15")

    stats = await service.compute(start_inclusive=start, end_exclusive=end, symbol=symbol, source="itest")

    assert stats.count == 1
    assert stats.take_profit_triggered == 0
    assert stats.stop_loss_triggered == 0
    assert stats.total_earned_usd == pytest.approx(0.0)
    assert stats.winning_deals == 0
    assert stats.losing_deals == 0
    assert stats.usd_diffs == []
