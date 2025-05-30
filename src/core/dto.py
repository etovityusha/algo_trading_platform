from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from src.core.enums import ActionEnum


class TradingSignal(BaseModel):
    symbol: str
    amount: Decimal
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    action: ActionEnum = ActionEnum.BUY
    source: str
