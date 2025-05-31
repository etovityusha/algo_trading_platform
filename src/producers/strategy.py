import abc
import dataclasses

from src.core.enums import ActionEnum


@dataclasses.dataclass
class Prediction:
    symbol: str
    action: ActionEnum


class Strategy(abc.ABC):
    @abc.abstractmethod
    async def predict(self, symbol: str) -> Prediction:
        pass
