import numpy as np
from numpy.typing import NDArray

from src.core.clients.interface import AbstractReadOnlyClient
from src.core.enums import ActionEnum
from src.producers.strategy import Prediction, Strategy


class MomentumStrategy(Strategy):
    """
    Агрессивная моментум-стратегия, основанная на техническом анализе.

    Использует комбинацию индикаторов:
    - RSI для определения перекупленности/перепроданности
    - MACD для определения силы тренда
    - Bollinger Bands для определения волатильности и точек входа
    - Stochastic Oscillator для подтверждения сигналов
    - Volume Analysis для подтверждения силы движения
    """

    def __init__(self, client: AbstractReadOnlyClient) -> None:
        self._client = client

    async def predict(self, symbol: str) -> Prediction:
        # Получаем больше свечей для более точного анализа
        candles = await self._client.get_candles(symbol, interval="15", limit=500)

        closes: NDArray[np.float64] = np.array([float(c.close) for c in candles])
        highs: NDArray[np.float64] = np.array([float(c.high) for c in candles])
        lows: NDArray[np.float64] = np.array([float(c.low) for c in candles])
        volumes: NDArray[np.float64] = np.array([float(c.volume) for c in candles])

        # Расчет индикаторов
        rsi = self._rsi(closes, period=14)
        macd_line, signal_line, macd_histogram = self._macd(closes)
        bb_upper, bb_middle, bb_lower = self._bollinger_bands(closes, period=20, std_dev=2.0)
        stoch_k, stoch_d = self._stochastic_oscillator(highs, lows, closes, k_period=14, d_period=3)
        atr = self._atr(highs, lows, closes, period=14)
        volume_sma = self._sma(volumes, period=20)

        # Текущие значения
        current_close = closes[-1]
        current_rsi = rsi[-1]
        current_macd = macd_line[-1]
        current_signal = signal_line[-1]
        current_macd_hist = macd_histogram[-1]
        prev_macd_hist = macd_histogram[-2]
        current_bb_upper = bb_upper[-1]
        current_bb_lower = bb_lower[-1]
        current_stoch_k = stoch_k[-1]
        current_stoch_d = stoch_d[-1]
        current_atr = atr[-1]
        current_volume = volumes[-1]
        avg_volume = volume_sma[-1]

        # Проверка на валидность данных
        if any(np.isnan([current_rsi, current_macd, current_signal, current_stoch_k, current_atr])):
            return Prediction(symbol=symbol, action=ActionEnum.NOTHING)

        # Агрессивные условия для входа в позицию
        action = ActionEnum.NOTHING
        stop_loss_percent = None
        take_profit_percent = None

        # Условия для ПОКУПКИ (агрессивные)
        buy_conditions = [
            # RSI показывает начало восходящего движения
            30 < current_rsi < 70,
            # MACD пересекает сигнальную линию вверх или растет
            current_macd > current_signal or (current_macd_hist > prev_macd_hist and current_macd_hist > 0),
            # Цена приближается к нижней полосе Боллинджера или отскакивает от нее
            current_close <= current_bb_lower * 1.05,
            # Stochastic показывает потенциал роста
            current_stoch_k > current_stoch_d and current_stoch_k < 80,
            # Повышенный объем (агрессивный фильтр)
            current_volume > avg_volume * 1.2,
        ]

        # Условия для ПРОДАЖИ (агрессивные)
        sell_conditions = [
            # RSI показывает начало нисходящего движения
            30 < current_rsi < 70,
            # MACD пересекает сигнальную линию вниз или падает
            current_macd < current_signal or (current_macd_hist < prev_macd_hist and current_macd_hist < 0),
            # Цена приближается к верхней полосе Боллинджера или отскакивает от нее
            current_close >= current_bb_upper * 0.95,
            # Stochastic показывает потенциал падения
            current_stoch_k < current_stoch_d and current_stoch_k > 20,
            # Повышенный объем (агрессивный фильтр)
            current_volume > avg_volume * 1.2,
        ]

        # Агрессивные параметры риска (более узкие стопы и широкие тейки)
        atr_multiplier_sl = 1.2  # Узкий стоп-лосс для агрессивной стратегии
        atr_multiplier_tp = 3.0  # Широкий тейк-профит для максимизации прибыли

        if sum(buy_conditions) >= 4:  # Требуем выполнения минимум 4 из 5 условий
            action = ActionEnum.BUY
            stop_loss_percent = (atr_multiplier_sl * current_atr / current_close) * 100
            take_profit_percent = (atr_multiplier_tp * current_atr / current_close) * 100

        elif sum(sell_conditions) >= 4:  # Требуем выполнения минимум 4 из 5 условий
            action = ActionEnum.SELL
            stop_loss_percent = (atr_multiplier_sl * current_atr / current_close) * 100
            take_profit_percent = (atr_multiplier_tp * current_atr / current_close) * 100

        return Prediction(symbol=symbol, action=action, stop_loss=stop_loss_percent, take_profit=take_profit_percent)

    @classmethod
    def _rsi(cls, values: NDArray[np.float64], period: int = 14) -> NDArray[np.float64]:
        """Relative Strength Index"""
        deltas = np.diff(values)
        gains = np.maximum(deltas, 0)
        losses = -np.minimum(deltas, 0)

        avg_gains = np.convolve(gains, np.ones(period), "valid") / period
        avg_losses = np.convolve(losses, np.ones(period), "valid") / period

        rs = np.divide(avg_gains, avg_losses, out=np.zeros_like(avg_gains), where=avg_losses != 0)
        rsi = 100 - (100 / (1 + rs))

        pad_length = len(values) - len(rsi)
        return np.concatenate([np.full(pad_length, np.nan), rsi])

    @classmethod
    def _macd(
        cls, values: NDArray[np.float64], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9
    ) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
        """MACD (Moving Average Convergence Divergence)"""
        ema_fast = cls._ema(values, fast_period)
        ema_slow = cls._ema(values, slow_period)
        macd_line = ema_fast - ema_slow
        signal_line = cls._ema(macd_line, signal_period)
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    @classmethod
    def _ema(cls, values: NDArray[np.float64], period: int) -> NDArray[np.float64]:
        """Exponential Moving Average"""
        alpha = 2 / (period + 1)
        ema = np.zeros_like(values)
        ema[0] = values[0]

        for i in range(1, len(values)):
            ema[i] = alpha * values[i] + (1 - alpha) * ema[i - 1]

        return ema

    @classmethod
    def _bollinger_bands(
        cls, values: NDArray[np.float64], period: int = 20, std_dev: float = 2.0
    ) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
        """Bollinger Bands"""
        sma = cls._sma(values, period)
        rolling_std = np.array([np.std(values[max(0, i - period + 1) : i + 1]) for i in range(len(values))])

        upper_band = sma + (rolling_std * std_dev)
        lower_band = sma - (rolling_std * std_dev)

        return upper_band, sma, lower_band

    @classmethod
    def _sma(cls, values: NDArray[np.float64], period: int) -> NDArray[np.float64]:
        """Simple Moving Average"""
        sma = np.convolve(values, np.ones(period), "valid") / period
        pad_length = len(values) - len(sma)
        return np.concatenate([np.full(pad_length, np.nan), sma])

    @classmethod
    def _stochastic_oscillator(
        cls,
        highs: NDArray[np.float64],
        lows: NDArray[np.float64],
        closes: NDArray[np.float64],
        k_period: int = 14,
        d_period: int = 3,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Stochastic Oscillator"""
        k_percent = []

        for i in range(len(closes)):
            if i < k_period - 1:
                k_percent.append(np.nan)
                continue

            period_high = np.max(highs[i - k_period + 1 : i + 1])
            period_low = np.min(lows[i - k_period + 1 : i + 1])

            if period_high == period_low:
                k_percent.append(50.0)
            else:
                k_percent.append(100 * (closes[i] - period_low) / (period_high - period_low))

        k_percent = np.array(k_percent)
        d_percent = cls._sma(k_percent, d_period)

        return k_percent, d_percent

    @classmethod
    def _atr(
        cls, highs: NDArray[np.float64], lows: NDArray[np.float64], closes: NDArray[np.float64], period: int = 14
    ) -> NDArray[np.float64]:
        """Average True Range"""
        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum.reduce([tr1, tr2, tr3])

        atr = np.convolve(tr, np.ones(period), "valid") / period
        pad_length = len(closes) - len(atr)
        return np.concatenate([np.full(pad_length, np.nan), atr])
