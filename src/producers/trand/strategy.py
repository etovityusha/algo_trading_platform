import numpy as np

from src.core.clients.interface import AbstractReadOnlyClient
from src.producers.strategy import Prediction, Strategy
from src.core.enums import ActionEnum


class TrandStrategy(Strategy):
    def __init__(self, client: AbstractReadOnlyClient) -> None:
        self._client = client

    async def predict(self, symbol: str) -> Prediction:
        candles = await self._client.get_candles(symbol, interval="30", limit=500)
        closes = np.array([float(c.close) for c in candles])
        highs = np.array([float(c.high) for c in candles])
        lows = np.array([float(c.low) for c in candles])

        ma_period = 20
        rsi_period = 14
        adx_period = 14

        ma = self._moving_average(closes, ma_period)
        rsi = self._relative_strength_index(closes, rsi_period)
        adx_val = self._adx(highs, lows, closes, adx_period)

        last_close = closes[-1]
        last_ma = ma[-1]
        last_rsi = rsi[-1]
        last_adx = adx_val[-1]

        action = ActionEnum.NOTHING
        if last_adx > 25:
            if last_close > last_ma and last_rsi < 70:
                action = ActionEnum.BUY
            elif last_close < last_ma and last_rsi > 30:
                action = ActionEnum.SELL
        return Prediction(symbol=symbol, action=action)

    @classmethod
    def _moving_average(cls, values, period):
        return np.convolve(values, np.ones(period), "valid") / period

    @classmethod
    def _relative_strength_index(cls, values, period=14):
        deltas = np.diff(values)
        ups = np.maximum(deltas, 0)
        downs = -np.minimum(deltas, 0)
        roll_up = np.convolve(ups, np.ones(period), "valid") / period
        roll_down = np.convolve(downs, np.ones(period), "valid") / period
        rs = np.divide(
            roll_up, roll_down, out=np.zeros_like(roll_up), where=roll_down != 0
        )
        rsi = 100 - (100 / (1 + rs))
        pad_length = len(values) - len(rsi)
        return np.concatenate([np.full(pad_length, np.nan), rsi])

    @classmethod
    def _adx(cls, high, low, close, period=14):
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

        plus_di = np.divide(
            100 * plus_di_raw, atr, out=np.zeros_like(atr), where=atr != 0
        )
        minus_di = np.divide(
            100 * minus_di_raw, atr, out=np.zeros_like(atr), where=atr != 0
        )
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
