import numpy as np
from numpy.typing import NDArray

from core.clients.dto import Candle
from core.enums import ActionEnum
from producers.strategy import Prediction, Strategy, StrategyConfig


class TrandStrategy(Strategy):
    def __init__(self, client, params: dict | None = None):
        """Initialize TrandStrategy with optional parameters.

        Args:
            client: Trading client instance
            params: Optional dict with strategy parameters:
                - ma_period: Moving average period (default: 20)
                - rsi_period: RSI period (default: 14)
                - adx_period: ADX period (default: 14)
                - atr_period: ATR period (default: 14)
                - adx_threshold: Minimum ADX for trade signal (default: 25)
                - rsi_buy: Maximum RSI for buy signal (default: 65)
                - rsi_sell: Minimum RSI for sell signal (default: 35)
                - volatility_threshold: Volatility filter multiplier (default: 0.8)
                - atr_sl_multiplier: ATR multiplier for stop loss (default: 1.5)
                - atr_tp_multiplier: ATR multiplier for take profit (default: 2.5)
        """
        super().__init__(client)
        self.params = params or {}

        # Extract parameters with defaults
        self.ma_period = self.params.get("ma_period", 20)
        self.rsi_period = self.params.get("rsi_period", 14)
        self.adx_period = self.params.get("adx_period", 14)
        self.atr_period = self.params.get("atr_period", 14)
        self.adx_threshold = self.params.get("adx_threshold", 25)
        self.rsi_buy = self.params.get("rsi_buy", 65)
        self.rsi_sell = self.params.get("rsi_sell", 35)
        self.volatility_threshold = self.params.get("volatility_threshold", 0.8)
        self.atr_sl_multiplier = self.params.get("atr_sl_multiplier", 1.5)
        self.atr_tp_multiplier = self.params.get("atr_tp_multiplier", 2.5)

    def get_config(self) -> StrategyConfig:
        """Get TrandStrategy configuration parameters."""
        return StrategyConfig(
            name="TrandStrategy",
            signal_interval_minutes=15,
            candle_interval="15",
            lookback_periods=200,  # Need 200 candles for analysis
            position_size_usd=100.0,  # Conservative position size
            description="Trend-following strategy using MA, RSI, ADX indicators",
        )

    async def _predict(self, symbol: str, candles: list[Candle]) -> Prediction:
        closes: NDArray[np.float64] = np.array([float(c.close) for c in candles])
        highs: NDArray[np.float64] = np.array([float(c.high) for c in candles])
        lows: NDArray[np.float64] = np.array([float(c.low) for c in candles])

        # Use instance parameters
        ma = self._moving_average(closes, self.ma_period)
        rsi = self._relative_strength_index(closes, self.rsi_period)
        adx_val = self._adx(highs, lows, closes, self.adx_period)

        # Add ATR calculation for dynamic SL/TP
        atr = self._average_true_range(highs, lows, closes, self.atr_period)

        last_close = closes[-1]
        last_ma = ma[-1]
        last_rsi = rsi[-1]
        last_adx = adx_val[-1]
        last_atr = atr[-1]

        # Volatility filter with configurable threshold
        volatility_filter = last_atr > np.mean(atr[-20:]) * self.volatility_threshold

        action = ActionEnum.NOTHING
        stop_loss_percent = None
        take_profit_percent = None

        if last_adx > self.adx_threshold and volatility_filter and not np.isnan(last_atr):
            # Use configurable RSI boundaries
            if last_close > last_ma and last_rsi < self.rsi_buy:
                action = ActionEnum.BUY
                # Calculate SL/TP with configurable multipliers
                calculated_sl = (self.atr_sl_multiplier * last_atr / last_close) * 100
                calculated_tp = (self.atr_tp_multiplier * last_atr / last_close) * 100
                # Apply min and max bounds
                stop_loss_percent = min(max(calculated_sl, 0.15), 10.0)  # Min 0.15%, Max 10%
                take_profit_percent = min(max(calculated_tp, 0.25), 15.0)  # Min 0.25%, Max 15%
            elif last_close < last_ma and last_rsi > self.rsi_sell:
                action = ActionEnum.SELL
                # Calculate SL/TP with configurable multipliers
                calculated_sl = (self.atr_sl_multiplier * last_atr / last_close) * 100
                calculated_tp = (self.atr_tp_multiplier * last_atr / last_close) * 100
                # Apply min and max bounds
                stop_loss_percent = min(max(calculated_sl, 0.15), 10.0)  # Min 0.15%, Max 10%
                take_profit_percent = min(max(calculated_tp, 0.25), 15.0)  # Min 0.25%, Max 15%

        return Prediction(
            symbol=symbol, action=action, stop_loss_percent=stop_loss_percent, take_profit_percent=take_profit_percent
        )

    @classmethod
    def _average_true_range(
        cls, high: NDArray[np.float64], low: NDArray[np.float64], close: NDArray[np.float64], period: int = 14
    ) -> NDArray[np.float64]:
        """Calculate Average True Range for volatility assessment"""
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
