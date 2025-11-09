"""Schemas for backtester messages and data structures."""

import datetime
from typing import Any

from pydantic import BaseModel, Field


class BacktestMessage(BaseModel):
    """Message schema for backtest requests via RabbitMQ.

    Contains all parameters needed to run a backtest without querying the database.
    """

    symbol: str = Field(..., description="Trading symbol (e.g., 'BTCUSDT')")
    strategy_name: str = Field(..., description="Name of the strategy to backtest")
    start_date: datetime.datetime = Field(..., description="Backtest start date")
    end_date: datetime.datetime = Field(..., description="Backtest end date")

    # Strategy configuration parameters
    signal_interval_minutes: int = Field(..., description="How often strategy generates signals")
    candle_interval: str = Field(..., description="Candle interval for analysis (e.g., '15', '60')")
    lookback_periods: int = Field(..., description="Number of historical candles needed")
    position_size_usd: float = Field(..., description="Position size in USD")

    # Strategy-specific parameters (optional)
    strategy_params: dict[str, Any] | None = Field(
        default=None, description="Additional strategy-specific parameters (e.g., ma_period, rsi_period)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "BTCUSDT",
                "strategy_name": "trand",
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-01-31T23:59:59",
                "signal_interval_minutes": 15,
                "candle_interval": "15",
                "lookback_periods": 200,
                "position_size_usd": 100.0,
                "strategy_params": {"ma_period": 20, "rsi_period": 14, "adx_period": 14, "adx_threshold": 25.0},
            }
        }
