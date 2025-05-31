from decimal import Decimal

from pydantic import BaseModel

from src.core.enums import ActionEnum


class TradingSignal(BaseModel):
    symbol: str
    amount: Decimal
    take_profit: float | None = None
    stop_loss: float | None = None
    action: ActionEnum = ActionEnum.BUY
    source: str
