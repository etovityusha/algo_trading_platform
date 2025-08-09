from __future__ import annotations

import datetime as dt
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.consumer.repositories.deal_repository import DealRepository
from src.core.clients.dto import Candle
from src.core.clients.interface import AbstractReadOnlyClient
from src.core.enums import ActionEnum
from src.models import Deal


@dataclass(slots=True)
class DealStats:
    count: int
    total_invested_usd: float
    avg_buy_price: float | None
    min_buy_price: float | None
    max_buy_price: float | None
    take_profit_triggered: int
    stop_loss_triggered: int
    # New required metrics
    total_earned_usd: float
    winning_deals: int
    losing_deals: int
    usd_diffs: list[float]


class StatisticsService:
    """Compute statistics on deals for a time window.

    Notes on returns:
    - Model currently stores executed BUY deals with optional take-profit/stop-loss levels
      and boolean flags indicating their execution.
    - We approximate realized PnL only for deals with execution flags. Open deals are
      excluded from realized-return metrics.
    - Quantity in storage represents invested quote amount (e.g., USDT) in tests; when
      using base quantity, the formula still approximates USD PnL by converting via entry.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        client: AbstractReadOnlyClient,
        *,
        candles_interval: str = "15",
    ) -> None:
        self._session_factory = session_factory
        self._client = client
        self._candles_interval = candles_interval

    async def compute(
        self,
        start_inclusive: dt.datetime,
        end_exclusive: dt.datetime,
        *,
        symbol: str | None = None,
        source: str | None = None,
    ) -> DealStats:
        async with self._session_factory() as session:
            repo = DealRepository(session=session)
            deals = await repo.list_by_period(
                start_inclusive=start_inclusive,
                end_exclusive=end_exclusive,
                symbol=symbol,
                source=source,
            )

        # Prefetch candles per symbol once to avoid redundant requests
        # We will use them twice: first with end_exclusive, then extend up to +7 days for unresolved deals
        extended_end = min(end_exclusive + dt.timedelta(days=7), dt.datetime.now(tz=dt.UTC))
        candles_by_symbol = await self._load_candles_for_deals(deals=deals, end_exclusive=extended_end)

        return self._compute_stats(deals, candles_by_symbol, end_exclusive, extended_end)

    def _compute_stats(
        self,
        deals: Iterable[Deal],
        candles_by_symbol: dict[str, list[Candle]],
        end_exclusive: dt.datetime,
        extended_end: dt.datetime,
    ) -> DealStats:
        deals_list = [d for d in deals if d.action == ActionEnum.BUY]
        count = len(deals_list)
        if count == 0:
            return DealStats(
                count=0,
                total_invested_usd=0.0,
                avg_buy_price=None,
                min_buy_price=None,
                max_buy_price=None,
                take_profit_triggered=0,
                stop_loss_triggered=0,
                total_earned_usd=0.0,
                winning_deals=0,
                losing_deals=0,
                usd_diffs=[],
            )

        total_invested_usd = 0.0
        prices: list[float] = []
        tp_count = 0
        sl_count = 0
        usd_diffs: list[float] = []
        winning_deals = 0
        losing_deals = 0

        for d in deals_list:
            if d.price is not None and d.qty is not None:
                qty_float = float(d.qty) if not isinstance(d.qty, float) else d.qty
                total_invested_usd += qty_float
                prices.append(d.price)

                entry = d.price
                take = d.take_profit_price
                stop = d.stop_loss_price

                # Determine closure by scanning historical candles after deal creation
                outcome, exit_price = self._infer_outcome(
                    deal=d,
                    candles=candles_by_symbol.get(d.symbol, []),
                    end_limit=end_exclusive,
                )

                if outcome is None and extended_end > end_exclusive:
                    # Try again within the next period (max one week ahead)
                    outcome, exit_price = self._infer_outcome(
                        deal=d,
                        candles=candles_by_symbol.get(d.symbol, []),
                        end_limit=extended_end,
                    )

                if outcome == "tp" and take is not None and exit_price is not None:
                    tp_count += 1
                    pnl = (exit_price - entry) * (qty_float / entry)
                    usd_diffs.append(float(pnl))
                    if pnl > 0:
                        winning_deals += 1
                    elif pnl < 0:
                        losing_deals += 1
                elif outcome == "sl" and stop is not None and exit_price is not None:
                    sl_count += 1
                    pnl = (exit_price - entry) * (qty_float / entry)
                    usd_diffs.append(float(pnl))
                    if pnl > 0:
                        winning_deals += 1
                    elif pnl < 0:
                        losing_deals += 1

        avg_price = sum(prices) / len(prices) if prices else None
        min_price = min(prices) if prices else None
        max_price = max(prices) if prices else None
        total_earned = sum(usd_diffs) if usd_diffs else 0.0

        return DealStats(
            count=count,
            total_invested_usd=float(total_invested_usd),
            avg_buy_price=avg_price,
            min_buy_price=min_price,
            max_buy_price=max_price,
            take_profit_triggered=tp_count,
            stop_loss_triggered=sl_count,
            total_earned_usd=float(total_earned),
            winning_deals=winning_deals,
            losing_deals=losing_deals,
            usd_diffs=usd_diffs,
        )

    async def _load_candles_for_deals(
        self, deals: Iterable[Deal], end_exclusive: dt.datetime
    ) -> dict[str, list[Candle]]:
        symbols = {d.symbol for d in deals}
        # Estimate required number of candles. Our API only supports "limit", so take a
        # reasonably large number to cover the period. 200 is the maximum per current client.
        # If period is larger, this will be a best-effort approximation.
        candles_by_symbol: dict[str, list[Candle]] = {}
        for symbol in symbols:
            candles = await self._client.get_candles(symbol=symbol, interval=self._candles_interval, limit=200)
            # Filter only candles up to end_exclusive to avoid using future bars
            end_ms = int(end_exclusive.timestamp() * 1000)
            candles_by_symbol[symbol] = [c for c in candles if c.timestamp <= end_ms]
        return candles_by_symbol

    def _infer_outcome(
        self, deal: Deal, candles: list[Candle], *, end_limit: dt.datetime
    ) -> tuple[str | None, float | None]:
        """
        Infer how the deal closed using price action after the deal was created.

        Returns tuple (outcome, exit_price):
        - outcome: "tp", "sl", or None if neither level was reached in available candles
        - exit_price: the assumed execution price (tp or sl level), or None

        If both TP and SL are touched within the same candle, we conservatively assume SL.
        """
        if deal.price is None:
            return None, None
        take = deal.take_profit_price
        stop = deal.stop_loss_price
        if take is None and stop is None:
            return None, None

        start_ms = int(deal.created_at.timestamp() * 1000)
        end_ms = int(end_limit.timestamp() * 1000)
        # Process candles strictly after the deal creation time
        for c in candles:
            if c.timestamp <= start_ms or c.timestamp > end_ms:
                continue
            # When both are set and both hit in same candle, assume SL first
            low_v = float(c.low)
            high_v = float(c.high)
            if stop is not None and low_v <= stop:
                return "sl", float(stop)
            if take is not None and high_v >= take:
                return "tp", float(take)
        return None, None
