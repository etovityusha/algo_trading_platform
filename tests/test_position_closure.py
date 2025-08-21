from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.consumer.services.trading import TradingService
from src.consumer.uow import UoWSession
from src.core.clients.dto import BuyResponse
from src.core.dto import TradingSignal
from src.core.enums import ActionEnum


@pytest.mark.asyncio
async def test_create_buy_position(async_session_factory):
    """Test creating a BUY position."""

    symbol = "BTCUSDT"
    source = "trand"

    async with async_session_factory() as session:
        async with session.begin():
            uow = UoWSession(session)

            buy_signal = TradingSignal(
                symbol=symbol,
                amount=Decimal("100"),
                take_profit=3.0,
                stop_loss=2.0,
                action=ActionEnum.BUY,
                source=source,
            )

            buy_response = BuyResponse(
                order_id="buy_123",
                symbol=symbol,
                qty=Decimal("0.002"),
                price=Decimal("50000"),
                stop_loss_price=Decimal("49000"),
                take_profit_price=Decimal("51500"),
            )

            buy_deal = await uow.deals.create_from_buy(buy_signal, buy_response)
            await session.flush()

            assert buy_deal.symbol == symbol
            assert buy_deal.action == ActionEnum.BUY
            assert buy_deal.source == source
            assert buy_deal.external_id == "buy_123"


@pytest.mark.asyncio
async def test_detect_open_position(async_session_factory):
    """Test detecting an open position."""

    symbol = "BTCUSDT"
    source = "trand"

    async with async_session_factory() as session:
        async with session.begin():
            uow = UoWSession(session)
            mock_client = AsyncMock()
            trading_service = TradingService(client=mock_client, uow_session=uow)

            # Create position
            buy_signal = TradingSignal(
                symbol=symbol,
                amount=Decimal("100"),
                take_profit=3.0,
                stop_loss=2.0,
                action=ActionEnum.BUY,
                source=source,
            )

            buy_response = BuyResponse(
                order_id="buy_123",
                symbol=symbol,
                qty=Decimal("0.002"),
                price=Decimal("50000"),
                stop_loss_price=Decimal("49000"),
                take_profit_price=Decimal("51500"),
            )

            await uow.deals.create_from_buy(buy_signal, buy_response)
            await session.flush()

            # Test detection
            has_open = await uow.deals.has_open_buy_for_symbol_by_source(symbol, source)
            position_status = await trading_service._get_position_status(symbol, source)

            assert has_open
            assert position_status.has_open_position
            assert not position_status.can_open_new


@pytest.mark.asyncio
async def test_prevent_duplicate_buy(async_session_factory):
    """Test that duplicate BUY positions are prevented."""

    symbol = "BTCUSDT"
    source = "trand"

    async with async_session_factory() as session:
        async with session.begin():
            uow = UoWSession(session)
            mock_client = AsyncMock()
            trading_service = TradingService(client=mock_client, uow_session=uow)

            # Create first position
            buy_signal = TradingSignal(
                symbol=symbol,
                amount=Decimal("100"),
                take_profit=3.0,
                stop_loss=2.0,
                action=ActionEnum.BUY,
                source=source,
            )

            buy_response = BuyResponse(
                order_id="buy_123",
                symbol=symbol,
                qty=Decimal("0.002"),
                price=Decimal("50000"),
                stop_loss_price=Decimal("49000"),
                take_profit_price=Decimal("51500"),
            )

            await uow.deals.create_from_buy(buy_signal, buy_response)
            await session.flush()

            # Test duplicate prevention
            position_status = await trading_service._get_position_status(symbol, source)
            assert not position_status.can_open_new


@pytest.mark.asyncio
async def test_close_position_with_sell_signal(async_session_factory):
    """Test closing position with SELL signal."""

    symbol = "BTCUSDT"
    source = "trand"

    async with async_session_factory() as session:
        uow = UoWSession(session)

        # Create mock client
        mock_client = AsyncMock()
        mock_client.sell.return_value = BuyResponse(
            order_id="sell_123",
            symbol=symbol,
            qty=Decimal("0.002"),
            price=Decimal("51000"),
            stop_loss_price=None,
            take_profit_price=None,
        )

        trading_service = TradingService(client=mock_client, uow_session=uow)

        # Create BUY position
        buy_signal = TradingSignal(
            symbol=symbol,
            amount=Decimal("100"),
            take_profit=3.0,
            stop_loss=2.0,
            action=ActionEnum.BUY,
            source=source,
        )

        buy_response = BuyResponse(
            order_id="buy_123",
            symbol=symbol,
            qty=Decimal("0.002"),
            price=Decimal("50000"),
            stop_loss_price=Decimal("49000"),
            take_profit_price=Decimal("51500"),
        )

        buy_deal = await uow.deals.create_from_buy(buy_signal, buy_response)

        # Process SELL signal
        sell_signal = TradingSignal(
            symbol=symbol,
            amount=Decimal("100"),
            take_profit=None,
            stop_loss=None,
            action=ActionEnum.SELL,
            source=source,
        )

        await trading_service._process_sell_signal(sell_signal)

        # Verify original position is marked as closed
        await session.refresh(buy_deal)
        assert buy_deal.is_manually_closed


@pytest.mark.asyncio
async def test_no_open_positions_after_closure(async_session_factory):
    """Test that no open positions exist after closure."""

    symbol = "BTCUSDT"
    source = "trand"

    async with async_session_factory() as session:
        uow = UoWSession(session)

        mock_client = AsyncMock()
        mock_client.sell.return_value = BuyResponse(
            order_id="sell_123",
            symbol=symbol,
            qty=Decimal("0.002"),
            price=Decimal("51000"),
            stop_loss_price=None,
            take_profit_price=None,
        )

        trading_service = TradingService(client=mock_client, uow_session=uow)

        # Create and close position
        buy_signal = TradingSignal(
            symbol=symbol,
            amount=Decimal("100"),
            take_profit=3.0,
            stop_loss=2.0,
            action=ActionEnum.BUY,
            source=source,
        )

        buy_response = BuyResponse(
            order_id="buy_123",
            symbol=symbol,
            qty=Decimal("0.002"),
            price=Decimal("50000"),
            stop_loss_price=Decimal("49000"),
            take_profit_price=Decimal("51500"),
        )

        await uow.deals.create_from_buy(buy_signal, buy_response)

        sell_signal = TradingSignal(
            symbol=symbol,
            amount=Decimal("100"),
            take_profit=None,
            stop_loss=None,
            action=ActionEnum.SELL,
            source=source,
        )

        await trading_service._process_sell_signal(sell_signal)

        # Check no open positions exist
        has_open = await uow.deals.has_open_buy_for_symbol_by_source(symbol, source)
        assert not has_open


@pytest.mark.asyncio
async def test_cooling_period_activation(async_session_factory):
    """Test that cooling period is activated after position closure."""

    symbol = "BTCUSDT"
    source = "trand"

    async with async_session_factory() as session:
        uow = UoWSession(session)

        mock_client = AsyncMock()
        mock_client.sell.return_value = BuyResponse(
            order_id="sell_123",
            symbol=symbol,
            qty=Decimal("0.002"),
            price=Decimal("51000"),
            stop_loss_price=None,
            take_profit_price=None,
        )

        trading_service = TradingService(client=mock_client, uow_session=uow)

        # Create and close position
        buy_signal = TradingSignal(
            symbol=symbol,
            amount=Decimal("100"),
            take_profit=3.0,
            stop_loss=2.0,
            action=ActionEnum.BUY,
            source=source,
        )

        buy_response = BuyResponse(
            order_id="buy_123",
            symbol=symbol,
            qty=Decimal("0.002"),
            price=Decimal("50000"),
            stop_loss_price=Decimal("49000"),
            take_profit_price=Decimal("51500"),
        )

        await uow.deals.create_from_buy(buy_signal, buy_response)

        sell_signal = TradingSignal(
            symbol=symbol,
            amount=Decimal("100"),
            take_profit=None,
            stop_loss=None,
            action=ActionEnum.SELL,
            source=source,
        )

        await trading_service._process_sell_signal(sell_signal)

        # Test cooling period
        position_status = await trading_service._get_position_status(symbol, source)
        assert not position_status.has_open_position
        assert position_status.recently_closed
        assert not position_status.can_open_new


@pytest.mark.asyncio
async def test_prevent_duplicate_sell(async_session_factory):
    """Test that duplicate SELL is prevented when no open position exists."""

    symbol = "BTCUSDT"
    source = "trand"

    async with async_session_factory() as session:
        uow = UoWSession(session)

        mock_client = AsyncMock()
        trading_service = TradingService(client=mock_client, uow_session=uow)

        # Try to sell without open position
        open_position = await uow.deals.get_open_position(symbol, source)
        assert open_position is None

        sell_signal = TradingSignal(
            symbol=symbol,
            amount=Decimal("100"),
            take_profit=None,
            stop_loss=None,
            action=ActionEnum.SELL,
            source=source,
        )

        result = await trading_service._process_sell_signal(sell_signal)
        assert result is None


@pytest.mark.asyncio
async def test_multiple_symbols_isolation(async_session_factory):
    """Test that closing one symbol doesn't affect others."""

    symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
    source = "trand"

    async with async_session_factory() as session:
        uow = UoWSession(session)

        mock_client = AsyncMock()
        mock_client.sell.return_value = BuyResponse(
            order_id="sell_ETHUSDT",
            symbol="ETHUSDT",
            qty=Decimal("0.1"),
            price=Decimal("1050"),
            stop_loss_price=None,
            take_profit_price=None,
        )

        trading_service = TradingService(client=mock_client, uow_session=uow)

        # Create positions for all symbols
        for symbol in symbols:
            buy_signal = TradingSignal(
                symbol=symbol,
                amount=Decimal("100"),
                take_profit=3.0,
                stop_loss=2.0,
                action=ActionEnum.BUY,
                source=source,
            )

            buy_response = BuyResponse(
                order_id=f"buy_{symbol}",
                symbol=symbol,
                qty=Decimal("0.1"),
                price=Decimal("1000"),
                stop_loss_price=Decimal("980"),
                take_profit_price=Decimal("1030"),
            )

            await uow.deals.create_from_buy(buy_signal, buy_response)

        # Close position for middle symbol only
        close_symbol = symbols[1]  # ETHUSDT

        sell_signal = TradingSignal(
            symbol=close_symbol,
            amount=Decimal("100"),
            take_profit=None,
            stop_loss=None,
            action=ActionEnum.SELL,
            source=source,
        )

        await trading_service._process_sell_signal(sell_signal)

        # Verify status for all symbols
        for symbol in symbols:
            position_status = await trading_service._get_position_status(symbol, source)

            if symbol == close_symbol:
                assert not position_status.has_open_position
                assert position_status.recently_closed
            else:
                assert position_status.has_open_position
                assert not position_status.recently_closed
