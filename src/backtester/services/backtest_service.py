import logging

from backtester.repositories.backtest_repository import BacktestRepository
from backtester.schemas import BacktestMessage
from core.backtest import Backtester
from core.clients.bybit_async import BybitAsyncClient
from producers.momentum.strategy import MomentumStrategy
from producers.strategy import Strategy, StrategyConfig
from producers.trand.strategy import TrandStrategy

logger = logging.getLogger(__name__)


class BacktestService:
    def __init__(
        self,
        repository: BacktestRepository,
        bybit_client: BybitAsyncClient,
    ) -> None:
        self._repository = repository
        self._bybit_client = bybit_client
        self._backtester = Backtester(bybit_client)

    async def process_backtest(self, message: BacktestMessage) -> None:
        """Process backtest request from message.

        Checks if result already exists, and runs backtest only if needed.
        """
        # Compute hash of parameters
        params_hash = self._repository.compute_params_hash(message)

        logger.info(
            f"Processing backtest request: {message.symbol} | {message.strategy_name} | "
            f"{message.start_date.date()} to {message.end_date.date()} | hash={params_hash[:8]}..."
        )

        # Check if result already exists
        existing_result = await self._repository.find_existing_result(params_hash)

        if existing_result:
            logger.info(
                f"Backtest result already exists (id={existing_result.id}): "
                f"trades={existing_result.total_trades}, "
                f"return={existing_result.total_return_percent:.2f}%, "
                f"win_rate={existing_result.win_rate:.2f}%"
            )
            return

        logger.info("No existing result found, running backtest...")

        try:
            # Create strategy with message parameters
            strategy = self._create_strategy(message)

            # Run backtest
            result = await self._backtester.run(
                strategy=strategy,
                symbol=message.symbol,
                start_date=message.start_date,
                end_date=message.end_date,
            )

            # Prepare trades data
            trades_data = {
                "trades": [
                    {
                        "symbol": trade.symbol,
                        "open_time": trade.open_time.isoformat(),
                        "open_price": float(trade.open_price),
                        "close_time": trade.close_time.isoformat() if trade.close_time else None,
                        "close_price": float(trade.close_price) if trade.close_price else None,
                        "tp_price": float(trade.tp_price),
                        "sl_price": float(trade.sl_price),
                        "position_size_usd": trade.position_size_usd,
                        "pnl_percent": trade.pnl_percent if trade.is_closed else None,
                        "income": float(trade.income) if trade.is_closed else None,
                    }
                    for trade in result.trades
                ]
            }

            # Save result with all parameters
            await self._repository.save_result(
                message=message,
                params_hash=params_hash,
                total_trades=result.total_trades,
                total_return_percent=result.total_return_percent,
                win_rate=result.win_rate,
                total_income=float(result.total_income),
                total_volume=float(result.total_volume),
                trades_data=trades_data,
            )

            logger.info(
                f"Backtest completed: "
                f"trades={result.total_trades}, return={result.total_return_percent:.2f}%, "
                f"win_rate={result.win_rate:.2f}%"
            )

        except Exception as e:
            logger.error(f"Error processing backtest: {e}", exc_info=True)
            raise

    def _create_strategy(self, message: BacktestMessage) -> Strategy:
        """Create strategy instance from message parameters."""
        logger.info(f"Creating strategy '{message.strategy_name}' with params: {message.strategy_params}")

        # Create strategy with custom config and parameters
        if message.strategy_name.lower() == "trand":
            strategy = TrandStrategy(self._bybit_client, params=message.strategy_params)
        elif message.strategy_name.lower() == "momentum":
            strategy = MomentumStrategy(self._bybit_client)
        else:
            raise ValueError(f"Unknown strategy: {message.strategy_name}")

        # Override strategy config with message parameters
        original_config = strategy.get_config()
        strategy._custom_config = StrategyConfig(
            name=original_config.name,
            signal_interval_minutes=message.signal_interval_minutes,
            candle_interval=message.candle_interval,
            lookback_periods=message.lookback_periods,
            position_size_usd=message.position_size_usd,
            description=original_config.description,
        )

        # Override get_config method to return custom config
        strategy.get_config = lambda: strategy._custom_config

        return strategy
