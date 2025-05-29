import dataclasses
from enums import ActionEnum


@dataclasses.dataclass
class Prediction:
    symbol: str
    action: ActionEnum
