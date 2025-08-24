import abc
import dataclasses
import datetime
from typing import NewType

from core.clients.dto import Candle
from core.clients.interface import AbstractReadOnlyClient
from src.core.enums import ActionEnum

Percent = NewType("Percent", float)


@dataclasses.dataclass
class Prediction:
    """
    Trading strategy prediction.

    Attributes:
        symbol: Trading symbol (e.g., 'BTCUSDT')
        action: Action (BUY, SELL, NOTHING)
        stop_loss_percent: Stop-loss as percentage of current price (0-100)
        take_profit_percent: Take-profit as percentage of current price (0-100)
    """

    symbol: str
    action: ActionEnum
    stop_loss_percent: Percent | None = None
    take_profit_percent: Percent | None = None

    def __post_init__(self):
        """Валидация прогноза после создания."""
        MIN_PERCENT = 0.1
        MAX_PERCENT = 50.0

        if self.action in (ActionEnum.BUY, ActionEnum.SELL):
            if self.stop_loss_percent is None:
                raise ValueError(f"stop_loss_percent is required for action {self.action}")
            if self.take_profit_percent is None:
                raise ValueError(f"take_profit_percent is required for action {self.action}")

            # Range validation
            if not (MIN_PERCENT <= self.stop_loss_percent <= MAX_PERCENT):
                raise ValueError(
                    f"stop_loss_percent must be between {MIN_PERCENT}% and {MAX_PERCENT}%, "
                    f"got {self.stop_loss_percent}%"
                )

            if not (MIN_PERCENT <= self.take_profit_percent <= MAX_PERCENT):
                raise ValueError(
                    f"take_profit_percent must be between {MIN_PERCENT}% and {MAX_PERCENT}%, "
                    f"got {self.take_profit_percent}%"
                )

        elif self.action == ActionEnum.NOTHING:
            if self.stop_loss_percent is not None or self.take_profit_percent is not None:
                raise ValueError("stop_loss_percent and take_profit_percent must be None for NOTHING action")

        if not self.symbol or not isinstance(self.symbol, str):
            raise ValueError("symbol must be a non-empty string")


@dataclasses.dataclass
class StrategyConfig:
    """
    Strategy configuration parameters required for backtesting.
    """

    name: str  # Strategy name for identification
    signal_interval_minutes: int  # How often strategy generates signals
    candle_interval: str  # Candle interval for analysis (e.g., '15', '60')
    lookback_periods: int  # Number of historical candles needed
    position_size_usd: float  # Default position size in USD
    description: str = ""  # Optional strategy description


class Strategy(abc.ABC):
    """
    Abstract base class for trading strategies.

    All strategies must implement predict() and provide configuration via get_config().
    """

    def __init__(self, client: AbstractReadOnlyClient) -> None:
        self._client = client

    @abc.abstractmethod
    async def _predict(self, symbol: str, candles: list[Candle]) -> Prediction:
        pass

    async def predict(self, symbol: str, prediction_time: datetime.datetime | None = None) -> Prediction:
        config = self.get_config()
        if prediction_time is None:
            start = None
        else:
            interval_minutes = datetime.timedelta(minutes=int(config.candle_interval))
            start = prediction_time - (interval_minutes * config.lookback_periods)
        candles = await self._client.get_candles(
            symbol=symbol,
            interval=config.candle_interval,
            limit=config.lookback_periods,
            start=start,
        )
        return await self._predict(symbol, candles)

    @abc.abstractmethod
    def get_config(self) -> StrategyConfig:
        """Get strategy configuration parameters."""
        pass
