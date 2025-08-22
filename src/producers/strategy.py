import abc
import dataclasses
from typing import NewType

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


class Strategy(abc.ABC):
    @abc.abstractmethod
    async def predict(self, symbol: str) -> Prediction:
        pass
