from dataclasses import dataclass
from decimal import Decimal


@dataclass
class BuyResponse:
    order_id: str | None
    symbol: str
    qty: Decimal
    price: Decimal


@dataclass
class Candle:
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    timestamp: int
