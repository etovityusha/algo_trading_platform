import enum


class ActionEnum(enum.Enum):
    BUY = 1
    SELL = 2
    NOTHING = 3


class ExchangeOrderStatus(str, enum.Enum):
    """Raw order statuses from exchange (Bybit)"""

    # Open statuses
    NEW = "New"
    PARTIALLY_FILLED = "PartiallyFilled"
    UNTRIGGERED = "Untriggered"

    # Closed statuses
    REJECTED = "Rejected"
    PARTIALLY_FILLED_CANCELED = "PartiallyFilledCanceled"
    FILLED = "Filled"
    CANCELLED = "Cancelled"
    TRIGGERED = "Triggered"
    DEACTIVATED = "Deactivated"


class PositionInternalStatus(enum.Enum):
    """Internal status for positions"""

    OPEN = "OPEN"
    CLOSED_BY_TP = "CLOSED_BY_TP"
    CLOSED_BY_SL = "CLOSED_BY_SL"
