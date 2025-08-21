import abc
import dataclasses

from src.core.enums import ActionEnum


@dataclasses.dataclass
class Prediction:
    symbol: str
    action: ActionEnum
    stop_loss: float | None = None  # в процентах от текущей цены
    take_profit: float | None = None  # в процентах от текущей цены


class Strategy(abc.ABC):
    @abc.abstractmethod
    async def predict(self, symbol: str) -> Prediction:
        pass
