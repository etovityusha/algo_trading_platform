import hashlib
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backtester.schemas import BacktestMessage
from models import BacktestResult


class BacktestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def compute_params_hash(message: BacktestMessage) -> str:
        """Compute a hash of backtest parameters for duplicate detection."""
        # Create a stable representation of all parameters
        params_dict = {
            "symbol": message.symbol,
            "strategy_name": message.strategy_name,
            "start_date": message.start_date.isoformat(),
            "end_date": message.end_date.isoformat(),
            "signal_interval_minutes": message.signal_interval_minutes,
            "candle_interval": message.candle_interval,
            "lookback_periods": message.lookback_periods,
            "position_size_usd": message.position_size_usd,
            "strategy_params": message.strategy_params or {},
        }

        # Convert to stable JSON string (sorted keys)
        params_json = json.dumps(params_dict, sort_keys=True)

        # Compute SHA256 hash
        return hashlib.sha256(params_json.encode()).hexdigest()

    async def find_existing_result(self, params_hash: str) -> BacktestResult | None:
        """Find existing backtest result by params hash."""
        stmt = select(BacktestResult).where(BacktestResult.params_hash == params_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_result(
        self,
        message: BacktestMessage,
        params_hash: str,
        total_trades: int,
        total_return_percent: float,
        win_rate: float,
        total_income: float,
        total_volume: float,
        trades_data: dict | None = None,
    ) -> BacktestResult:
        """Save backtest result with all parameters."""
        result = BacktestResult(
            params_hash=params_hash,
            symbol=message.symbol,
            strategy_name=message.strategy_name,
            start_date=message.start_date,
            end_date=message.end_date,
            signal_interval_minutes=message.signal_interval_minutes,
            candle_interval=message.candle_interval,
            lookback_periods=message.lookback_periods,
            position_size_usd=message.position_size_usd,
            strategy_params=message.strategy_params,
            total_trades=total_trades,
            total_return_percent=total_return_percent,
            win_rate=win_rate,
            total_income=total_income,
            total_volume=total_volume,
            trades_data=trades_data,
        )
        self._session.add(result)
        await self._session.commit()
        await self._session.refresh(result)
        return result
