import datetime
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from core.clients.bybit_async import BybitAsyncClient
from core.clients.dto import Candle
from core.enums import ActionEnum
from producers.strategy import Prediction, Strategy


@dataclass
class Trade:
    symbol: str
    open_time: datetime.datetime
    open_price: Decimal
    tp_price: Decimal
    sl_price: Decimal
    close_time: datetime.datetime | None = None
    close_price: Decimal | None = None
    position_size_usd: float = 0.0

    @property
    def is_closed(self) -> bool:
        return self.close_time is not None and self.close_price is not None

    @property
    def pnl_percent(self) -> float:
        if not self.is_closed:
            return 0.0
        if self.close_price is None:
            raise ValueError
        return float((self.close_price - self.open_price) / self.open_price * 100)

    @property
    def volume(self) -> Decimal:
        return Decimal(self.position_size_usd * 2)

    @property
    def income(self) -> Decimal:
        if not self.is_closed:
            return Decimal(0)
        units = Decimal(self.position_size_usd) / self.open_price
        if self.close_price is None:
            raise ValueError
        return (self.close_price - self.open_price) * units


@dataclass
class BacktestResult:
    trades: list[Trade]
    total_return_percent: float
    win_rate: float
    total_trades: int
    total_income: Decimal
    total_volume: Decimal


class Backtester:
    def __init__(self, client: BybitAsyncClient):
        self._client = client

    async def run(
        self, strategy: Strategy, symbol: str, start_date: datetime.datetime, end_date: datetime.datetime
    ) -> BacktestResult:
        config = strategy.get_config()

        # Загружаем все необходимые свечи
        candles = await self._load_candles(symbol, config, start_date, end_date)
        candles_dict = {c.timestamp: c for c in candles}

        trades: list[Trade] = []
        current_position: Trade | None = None

        # Проходим по времени с интервалом сигнала
        current_time = start_date
        signal_interval = datetime.timedelta(minutes=config.signal_interval_minutes)

        while current_time <= end_date:
            # Получаем свечи для анализа
            analysis_candles = self._get_candles_for_analysis(candles_dict, current_time, config)

            if len(analysis_candles) >= config.lookback_periods:
                prediction: Prediction = await strategy._predict(symbol, analysis_candles)
                current_candle = analysis_candles[-1]

                # Обрабатываем сигналы
                if prediction.action.value == ActionEnum.BUY.value and current_position is None:
                    # Открываем позицию
                    current_position = Trade(
                        symbol=symbol,
                        open_time=current_time,
                        open_price=current_candle.close,
                        position_size_usd=config.position_size_usd,
                        tp_price=current_candle.close * Decimal(1 + prediction.take_profit_percent / 100),
                        sl_price=current_candle.close * Decimal(1 - prediction.stop_loss_percent / 100),
                    )
                    print(f"Открываем сделку {current_time} по цене {current_candle.close}")
                elif current_position is not None and (
                    prediction.action.value == ActionEnum.SELL.value
                    or current_candle.close < current_position.sl_price
                    or current_candle.close >= current_position.tp_price
                ):
                    current_position.close_time = current_time
                    current_position.close_price = current_candle.close
                    trades.append(current_position)
                    print(
                        f"Закрываем сделку {current_time} по цене {current_candle.close}, Доход {round(current_position.income, 2)}",
                        end="\n\n",
                    )
                    current_position = None

            current_time += signal_interval
        # Закрываем открытую позицию в конце периода
        if current_position is not None:
            final_candles = self._get_candles_for_analysis(candles_dict, end_date, config)
            if final_candles:
                current_position.close_time = end_date
                current_position.close_price = final_candles[-1].close
                trades.append(current_position)

        return self._calculate_results(trades)

    async def _load_candles(
        self, symbol: str, config: Any, start_date: datetime.datetime, end_date: datetime.datetime
    ) -> list[Candle]:
        # Добавляем буфер для lookback_periods
        lookback_duration = datetime.timedelta(minutes=int(config.candle_interval) * config.lookback_periods)
        actual_start = start_date - lookback_duration

        all_candles: list[Candle] = []
        current_start = actual_start

        while current_start < end_date:
            candles = await self._client.get_candles(
                symbol=symbol, interval=config.candle_interval, limit=1000, start=current_start
            )

            if not candles:
                break

            all_candles.extend(candles)
            # Переходим к следующей порции - добавляем интервал к последней свече
            last_timestamp = max(c.timestamp for c in candles)
            current_start = datetime.datetime.fromtimestamp(last_timestamp / 1000) + datetime.timedelta(
                minutes=int(config.candle_interval)
            )

            # Если получили меньше 1000 свеч, значит достигли конца данных
            if len(candles) < 1000:
                break

        # Сортируем по времени и фильтруем дубликаты
        unique_candles = {c.timestamp: c for c in all_candles}
        return sorted(unique_candles.values(), key=lambda x: x.timestamp)

    def _get_candles_for_analysis(
        self, candles_dict: dict[int, Candle], current_time: datetime.datetime, config: Any
    ) -> list[Candle]:
        current_timestamp = int(current_time.timestamp() * 1000)

        # Находим все свечи до current_time и берем последние lookback_periods
        available_candles = [candle for timestamp, candle in candles_dict.items() if timestamp <= current_timestamp]

        # Сортируем по времени и берем последние lookback_periods свечей
        available_candles.sort(key=lambda x: x.timestamp)
        return available_candles[-config.lookback_periods :]

    def _calculate_results(self, trades: list[Trade]) -> BacktestResult:
        closed_trades = [t for t in trades if t.is_closed]

        if not closed_trades:
            return BacktestResult(
                trades=trades,
                total_return_percent=0,
                win_rate=0,
                total_trades=0,
                total_income=Decimal(0),
                total_volume=Decimal(0),
            )

        total_return = sum(t.pnl_percent for t in closed_trades)
        winning_trades = len([t for t in closed_trades if t.pnl_percent > 0])
        win_rate = winning_trades / len(closed_trades) * 100
        total_income = Decimal(sum(t.income for t in closed_trades))
        total_volume = Decimal(sum(t.volume for t in closed_trades))
        return BacktestResult(
            trades=trades,
            total_return_percent=total_return,
            win_rate=win_rate,
            total_trades=len(closed_trades),
            total_income=total_income,
            total_volume=total_volume,
        )
