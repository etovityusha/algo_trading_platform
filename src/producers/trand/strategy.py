import numpy as np
from numpy.typing import NDArray

from src.core.clients.interface import AbstractReadOnlyClient
from src.core.enums import ActionEnum
from src.producers.strategy import Prediction, Strategy


class TrandStrategy(Strategy):
    def __init__(self, client: AbstractReadOnlyClient) -> None:
        self._client = client

    async def predict(self, symbol: str) -> Prediction:
        candles = await self._client.get_candles(symbol, interval="60", limit=200)
        closes: NDArray[np.float64] = np.array([float(c.close) for c in candles])
        highs: NDArray[np.float64] = np.array([float(c.high) for c in candles])
        lows: NDArray[np.float64] = np.array([float(c.low) for c in candles])

        ma_period: int = 20
        rsi_period: int = 14
        adx_period: int = 14

        ma = self._moving_average(closes, ma_period)
        rsi = self._relative_strength_index(closes, rsi_period)
        adx_val = self._adx(highs, lows, closes, adx_period)

        # Добавляем расчет ATR для динамических SL/TP
        atr = self._average_true_range(highs, lows, closes, 14)

        last_close = closes[-1]
        last_ma = ma[-1]
        last_rsi = rsi[-1]
        last_adx = adx_val[-1]
        last_atr = atr[-1]

        # Фильтр по волатильности
        volatility_filter = last_atr > np.mean(atr[-20:]) * 0.8

        action = ActionEnum.NOTHING
        stop_loss_percent = None
        take_profit_percent = None

        if last_adx > 25 and volatility_filter and not np.isnan(last_atr):
            # Улучшенные границы RSI
            if last_close > last_ma and last_rsi < 65:
                action = ActionEnum.BUY
                # SL и TP для покупки
                stop_loss_percent = (1.5 * last_atr / last_close) * 100  # 1.5 ATR вниз
                take_profit_percent = (2.5 * last_atr / last_close) * 100  # 2.5 ATR вверх
            elif last_close < last_ma and last_rsi > 35:
                action = ActionEnum.SELL
                # SL и TP для продажи
                stop_loss_percent = (1.5 * last_atr / last_close) * 100  # 1.5 ATR вверх
                take_profit_percent = (2.5 * last_atr / last_close) * 100  # 2.5 ATR вниз

        return Prediction(symbol=symbol, action=action, stop_loss=stop_loss_percent, take_profit=take_profit_percent)

    @classmethod
    def _average_true_range(
        cls, high: NDArray[np.float64], low: NDArray[np.float64], close: NDArray[np.float64], period: int = 14
    ) -> NDArray[np.float64]:
        """Расчет Average True Range для определения волатильности"""
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum.reduce([tr1, tr2, tr3])
        atr = np.convolve(tr, np.ones(period), "valid") / period
        pad_length = len(close) - len(atr)
        return np.concatenate([np.full(pad_length, np.nan), atr])

    @classmethod
    def _moving_average(cls, values: NDArray[np.float64], period: int) -> NDArray[np.float64]:
        return np.convolve(values, np.ones(period), "valid") / period

    @classmethod
    def _relative_strength_index(cls, values: NDArray[np.float64], period: int = 14) -> NDArray[np.float64]:
        deltas = np.diff(values)
        ups = np.maximum(deltas, 0)
        downs = -np.minimum(deltas, 0)
        roll_up = np.convolve(ups, np.ones(period), "valid") / period
        roll_down = np.convolve(downs, np.ones(period), "valid") / period
        rs = np.divide(roll_up, roll_down, out=np.zeros_like(roll_up), where=roll_down != 0)
        rsi = 100 - (100 / (1 + rs))
        pad_length = len(values) - len(rsi)
        return np.concatenate([np.full(pad_length, np.nan), rsi])

    @classmethod
    def _adx(
        cls,
        high: NDArray[np.float64],
        low: NDArray[np.float64],
        close: NDArray[np.float64],
        period: int = 14,
    ) -> NDArray[np.float64]:
        plus_dm = np.diff(high, prepend=high[0])
        minus_dm = np.diff(low, prepend=low[0])
        plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)
        minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0)

        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum.reduce([tr1, tr2, tr3])

        atr = np.convolve(tr, np.ones(period), "valid") / period

        plus_di_raw = np.convolve(plus_dm[1:], np.ones(period), "valid") / period
        minus_di_raw = np.convolve(minus_dm[1:], np.ones(period), "valid") / period
        plus_di = np.divide(100 * plus_di_raw, atr, out=np.zeros_like(atr), where=atr != 0)
        minus_di = np.divide(100 * minus_di_raw, atr, out=np.zeros_like(atr), where=atr != 0)
        denom = plus_di + minus_di
        dx = np.divide(
            100 * np.abs(plus_di - minus_di),
            denom,
            out=np.zeros_like(denom),
            where=denom != 0,
        )
        adx_arr = np.convolve(dx, np.ones(period), "valid") / period
        pad_length = len(close) - len(adx_arr)
        return np.concatenate([np.full(pad_length, np.nan), adx_arr])
