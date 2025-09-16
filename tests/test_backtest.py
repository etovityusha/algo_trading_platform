import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from core.backtest import Backtester, BacktestResult, Trade
from core.clients.dto import Candle
from core.enums import ActionEnum
from producers.strategy import Prediction, Strategy, StrategyConfig


class MockStrategy(Strategy):
    def __init__(self, client, predictions: list[ActionEnum]):
        super().__init__(client)
        self.predictions = predictions
        self.call_count = 0

    def get_config(self) -> StrategyConfig:
        return StrategyConfig(
            name="MockStrategy",
            signal_interval_minutes=60,
            candle_interval="60",
            lookback_periods=10,
            position_size_usd=100.0,
        )

    async def _predict(self, symbol: str, candles: list[Candle]) -> Prediction:
        if self.call_count < len(self.predictions):
            action = self.predictions[self.call_count]
        else:
            action = ActionEnum.NOTHING

        self.call_count += 1

        if action in [ActionEnum.BUY, ActionEnum.SELL]:
            return Prediction(
                symbol=symbol,
                action=action,
                stop_loss_percent=2.0,
                take_profit_percent=4.0,
            )
        return Prediction(symbol=symbol, action=action)


@pytest.fixture
def mock_client():
    client = Mock()
    # Создаем тестовые свечи начиная с более раннего времени для lookback_periods
    candles = []
    base_time = datetime.datetime(2023, 12, 30)  # Начинаем раньше для исторических данных
    for i in range(100):
        timestamp = int((base_time + datetime.timedelta(hours=i)).timestamp() * 1000)
        candles.append(
            Candle(
                timestamp=timestamp,
                open=Decimal("50000"),
                high=Decimal("51000"),
                low=Decimal("49000"),
                close=Decimal("50500") if i % 2 == 0 else Decimal("49500"),
                volume=Decimal("100"),
            )
        )

    client.get_candles = AsyncMock(return_value=candles)
    return client


@pytest.fixture
def backtester(mock_client):
    return Backtester(mock_client)


class TestTrade:
    def test_trade_creation(self):
        trade = Trade(
            symbol="BTCUSDT",
            open_time=datetime.datetime.now(),
            open_price=Decimal("50000"),
        )
        assert trade.symbol == "BTCUSDT"
        assert not trade.is_closed
        assert trade.pnl_percent == 0.0

    def test_trade_closed(self):
        trade = Trade(
            symbol="BTCUSDT",
            open_time=datetime.datetime.now(),
            open_price=Decimal("50000"),
            close_time=datetime.datetime.now(),
            close_price=Decimal("55000"),
        )
        assert trade.is_closed
        assert trade.pnl_percent == 10.0  # (55000 - 50000) / 50000 * 100

    def test_trade_loss(self):
        trade = Trade(
            symbol="BTCUSDT",
            open_time=datetime.datetime.now(),
            open_price=Decimal("50000"),
            close_time=datetime.datetime.now(),
            close_price=Decimal("45000"),
        )
        assert trade.is_closed
        assert trade.pnl_percent == -10.0  # (45000 - 50000) / 50000 * 100


class TestBacktester:
    @pytest.mark.asyncio
    async def test_no_trades(self, backtester, mock_client):
        strategy = MockStrategy(mock_client, [ActionEnum.NOTHING])

        start_date = datetime.datetime(2024, 1, 1)
        end_date = datetime.datetime(2024, 1, 2)

        result = await backtester.run(strategy, "BTCUSDT", start_date, end_date)

        assert isinstance(result, BacktestResult)
        assert result.total_trades == 0
        assert result.total_return_percent == 0.0
        assert result.win_rate == 0.0

    @pytest.mark.asyncio
    async def test_multiple_trades(self, backtester, mock_client):
        # Несколько циклов BUY-SELL
        strategy = MockStrategy(mock_client, [ActionEnum.BUY, ActionEnum.SELL, ActionEnum.BUY, ActionEnum.SELL])

        start_date = datetime.datetime(2024, 1, 1)
        end_date = datetime.datetime(2024, 1, 1, 6)  # 6 часов

        result = await backtester.run(strategy, "BTCUSDT", start_date, end_date)

        assert result.total_trades == 2
        assert len(result.trades) == 2
        assert all(trade.is_closed for trade in result.trades)

    @pytest.mark.asyncio
    async def test_open_position_at_end(self, backtester, mock_client):
        # Только BUY, без SELL
        strategy = MockStrategy(mock_client, [ActionEnum.BUY])

        start_date = datetime.datetime(2024, 1, 1)
        end_date = datetime.datetime(2024, 1, 1, 2)

        result = await backtester.run(strategy, "BTCUSDT", start_date, end_date)

        assert result.total_trades == 1
        assert result.trades[0].is_closed  # Должна закрыться в конце

    @pytest.mark.asyncio
    async def test_ignore_sell_without_position(self, backtester, mock_client):
        # SELL без открытой позиции должен игнорироваться
        strategy = MockStrategy(mock_client, [ActionEnum.SELL, ActionEnum.BUY])

        start_date = datetime.datetime(2024, 1, 1)
        end_date = datetime.datetime(2024, 1, 1, 3)

        result = await backtester.run(strategy, "BTCUSDT", start_date, end_date)

        # Должна быть только одна открытая позиция от BUY
        assert len(result.trades) == 1

    @pytest.mark.asyncio
    async def test_ignore_buy_with_open_position(self, backtester, mock_client):
        # Второй BUY должен игнорироваться
        strategy = MockStrategy(mock_client, [ActionEnum.BUY, ActionEnum.BUY, ActionEnum.SELL])

        start_date = datetime.datetime(2024, 1, 1)
        end_date = datetime.datetime(2024, 1, 1, 4)

        result = await backtester.run(strategy, "BTCUSDT", start_date, end_date)

        # Должна быть только одна сделка
        assert result.total_trades == 1


class TestBacktestResult:
    def test_empty_result(self):
        result = BacktestResult(trades=[], total_return_percent=0.0, win_rate=0.0, total_trades=0)
        assert result.total_trades == 0
        assert result.total_return_percent == 0.0
        assert result.win_rate == 0.0

    def test_result_with_trades(self):
        trades = [
            Trade(
                "BTCUSDT", datetime.datetime.now(), Decimal("50000"), datetime.datetime.now(), Decimal("55000")
            ),  # +10%
            Trade(
                "BTCUSDT", datetime.datetime.now(), Decimal("50000"), datetime.datetime.now(), Decimal("45000")
            ),  # -10%
        ]

        result = BacktestResult(
            trades=trades,
            total_return_percent=0.0,  # 10% - 10% = 0%
            win_rate=50.0,  # 1 из 2 прибыльных
            total_trades=2,
        )

        assert result.total_trades == 2
        assert result.win_rate == 50.0


if __name__ == "__main__":
    pytest.main([__file__])
