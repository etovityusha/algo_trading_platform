import dataclasses
from decimal import Decimal
from typing import TYPE_CHECKING

from pydantic import BaseModel

from src.core.enums import ActionEnum

if TYPE_CHECKING:
    from src.models import Deal


@dataclasses.dataclass
class PositionStatus:
    has_open_position: bool
    open_position: "Deal | None" = None
    recently_closed: bool = False
    can_open_new: bool = False


class TradingSignal(BaseModel):
    symbol: str
    amount: Decimal
    take_profit: float | None = None
    stop_loss: float | None = None
    action: ActionEnum = ActionEnum.BUY
    source: str
