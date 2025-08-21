from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.consumer.services.position_manager import PositionManagerService
from src.core.enums import ActionEnum
from tests.conftest import DataManager, MockReadOnlyClient


@pytest.mark.asyncio
async def test_handle_open_positions_no_positions(position_manager_service: PositionManagerService, caplog):
    """Test handling when no open positions exist"""
    await position_manager_service.handle_open_positions()


@pytest.mark.asyncio
async def test_handle_open_positions_position_still_open(
    position_manager_service: PositionManagerService,
    mock_read_client: MockReadOnlyClient,
    test_data_manager: DataManager,
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Test handling position that remains open (price between SL and TP)"""
    # Create test position
    sample_position = await test_data_manager.create_deal(
        symbol="BTCUSDT",
        qty=Decimal("0.5"),
        price=100.0,
        take_profit_price=102.0,
        stop_loss_price=98.0,
        action=ActionEnum.BUY,
        source="test_source",
    )

    # Set current price between stop loss (98) and take profit (102)
    mock_read_client.set_ticker_price("BTCUSDT", Decimal("100.0"))

    await position_manager_service.handle_open_positions()

    # Verify position is still marked as open in database
    updated_deal = await test_data_manager.get_deal(sample_position.id)
    assert not updated_deal.is_take_profit_executed
    assert not updated_deal.is_stop_loss_executed
    assert not updated_deal.is_manually_closed


@pytest.mark.asyncio
async def test_handle_open_positions_take_profit_triggered(
    position_manager_service: PositionManagerService,
    mock_read_client: MockReadOnlyClient,
    test_data_manager: DataManager,
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Test handling position closed by take profit"""
    # Create test position
    sample_position = await test_data_manager.create_deal(
        symbol="BTCUSDT",
        qty=Decimal("0.5"),
        price=100.0,
        take_profit_price=102.0,
        stop_loss_price=98.0,
        action=ActionEnum.BUY,
        source="test_source",
    )

    # Set current price above take profit (102)
    mock_read_client.set_ticker_price("BTCUSDT", Decimal("103.0"))

    await position_manager_service.handle_open_positions()

    # Verify position is marked as TP executed in database
    updated_deal = await test_data_manager.get_deal(sample_position.id)
    assert not updated_deal.is_stop_loss_executed
    assert not updated_deal.is_manually_closed
    assert updated_deal.is_take_profit_executed


@pytest.mark.asyncio
async def test_handle_open_positions_stop_loss_triggered(
    position_manager_service: PositionManagerService,
    mock_read_client: MockReadOnlyClient,
    test_data_manager: DataManager,
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Test handling position closed by stop loss"""
    # Create test position
    sample_position = await test_data_manager.create_deal(
        symbol="BTCUSDT",
        qty=Decimal("0.5"),
        price=100.0,
        take_profit_price=102.0,
        stop_loss_price=98.0,
        action=ActionEnum.BUY,
        source="test_source",
    )

    # Set current price below stop loss (98)
    mock_read_client.set_ticker_price("BTCUSDT", Decimal("97.0"))

    await position_manager_service.handle_open_positions()

    # Verify position is marked as SL executed in database
    updated_deal = await test_data_manager.get_deal(sample_position.id)
    assert not updated_deal.is_take_profit_executed
    assert updated_deal.is_stop_loss_executed
    assert not updated_deal.is_manually_closed


@pytest.mark.asyncio
async def test_handle_multiple_open_positions(
    position_manager_service: PositionManagerService,
    mock_read_client: MockReadOnlyClient,
    test_data_manager: DataManager,
    async_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Test handling multiple open positions with different outcomes"""
    # Create multiple positions with different symbols
    deals_data = [
        {
            "external_id": "order_1",
            "symbol": "BTCUSDT",
            "qty": Decimal("0.5"),
            "price": 100.0,
            "take_profit_price": 105.0,
            "stop_loss_price": 95.0,
            "action": ActionEnum.BUY,
            "source": "test_source",
        },
        {
            "external_id": "order_2",
            "symbol": "ETHUSDT",
            "qty": Decimal("1.0"),
            "price": 200.0,
            "take_profit_price": 210.0,
            "stop_loss_price": 190.0,
            "action": ActionEnum.BUY,
            "source": "test_source",
        },
        {
            "external_id": "order_3",
            "symbol": "ADAUSDT",
            "qty": Decimal("100.0"),
            "price": 1.0,
            "take_profit_price": 1.1,
            "stop_loss_price": 0.9,
            "action": ActionEnum.BUY,
            "source": "test_source",
        },
    ]

    created_deals = await test_data_manager.create_multiple_deals(deals_data)
    position1, position2, position3 = created_deals

    # Set prices: BTC hits TP, ETH hits SL, ADA stays open
    mock_read_client.set_ticker_price("BTCUSDT", Decimal("106.0"))  # Above TP
    mock_read_client.set_ticker_price("ETHUSDT", Decimal("185.0"))  # Below SL
    mock_read_client.set_ticker_price("ADAUSDT", Decimal("1.05"))  # Between SL and TP

    await position_manager_service.handle_open_positions()

    # Verify each position's final state
    btc_deal = await test_data_manager.get_deal(position1.id)
    assert btc_deal.is_take_profit_executed
    assert not btc_deal.is_stop_loss_executed

    eth_deal = await test_data_manager.get_deal(position2.id)
    assert not eth_deal.is_take_profit_executed
    assert eth_deal.is_stop_loss_executed

    ada_deal = await test_data_manager.get_deal(position3.id)
    assert not ada_deal.is_take_profit_executed
    assert not ada_deal.is_stop_loss_executed
