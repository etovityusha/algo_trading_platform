from dataclasses import dataclass
from decimal import Decimal

from pydantic import BaseModel

from core.enums import ExchangeOrderStatus


@dataclass
class BuyResponse:
    order_id: str | None
    symbol: str
    qty: Decimal
    price: Decimal
    stop_loss_price: Decimal | None
    take_profit_price: Decimal | None


@dataclass
class Candle:
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    timestamp: int


class OrderStatus(BaseModel):
    order_id: str
    order_link_id: str
    symbol: str
    order_status: ExchangeOrderStatus  # Raw string status from exchange
    side: str
    order_type: str
    qty: str
    price: str
    avg_price: str | None
    cum_exec_qty: str
    stop_order_type: str
    created_time: str
    updated_time: str
