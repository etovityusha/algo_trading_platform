# Algorithmic Trading System

This project is a microservice-based algorithmic trading system that interacts with the Bybit cryptocurrency exchange. It consists of multiple producers that generate trading signals and a consumer that executes trades based on these signals.

## 🏗️ Architecture

The system consists of the following main components:

- **Producers**: Microservices that generate trading signals based on different strategies
  - `trand`: A trend-following strategy implementation
- **Consumer**: Service that processes trading signals and executes trades on Bybit
- **RabbitMQ**: Message broker for communication between producers and consumer
- **PostgreSQL**: Database for storing trade history and system state


## 🔄 Trading Service (Consumer)

The Trading Service is the core component that processes trading signals from producers and executes trades. It implements sophisticated position management with risk controls and prevents duplicate operations.

### Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Producers     │───▶│   RabbitMQ      │───▶│ Trading Service │
│  (Strategies)   │    │   (Queue)       │    │  (Consumer)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │  Bybit Exchange │
                                               │   + Database    │
                                               └─────────────────┘
```

### Signal Processing Flow

#### 1. Signal Reception
The Trading Service receives trading signals from the message queue containing:
- **Symbol**: Trading pair (e.g., "BTCUSDT")
- **Amount**: USD amount to trade
- **Take Profit**: Target profit percentage (optional)
- **Stop Loss**: Risk limit percentage (optional) 
- **Action**: BUY, SELL, or NOTHING
- **Source**: Strategy identifier for position tracking

#### 2. Position Management Logic

**For BUY Signals:**

1. **Position Status Check**: Verify no existing open position for this symbol+source combination
2. **Duplicate Prevention**: Block signal if position already exists or was recently closed (cooling period)
3. **Risk Validation**: Use signal's SL/TP values, or apply defaults (2% stop loss, 3% take profit)
4. **Exchange Execution**: Place buy order with calculated stop loss and take profit levels
5. **Database Recording**: Store deal record with order details and strategy source
6. **Transaction Commit**: Ensure all changes are persisted atomically

**For SELL Signals:**

1. **Position Lookup**: Find existing open position for this symbol+source combination
2. **Validation**: Skip if no open position exists (prevents erroneous sells)
3. **Market Execution**: Execute sell order for entire position quantity at current market price
4. **Position Closure**: Mark original BUY position as manually closed in database
5. **Sell Recording**: Create new SELL deal record with execution details
6. **Transaction Commit**: Ensure both position closure and sell record are saved

### Position Status Management

The Trading Service maintains comprehensive position tracking using a `PositionStatus` dataclass with four key attributes:

- **has_open_position**: Whether an active position currently exists
- **open_position**: The actual position record with quantities and prices (or None)
- **recently_closed**: Whether a position was closed in the last 60 minutes
- **can_open_new**: Combined status indicating if a new position is allowed

#### Rules:
- **No Duplicates**: Only one open position per symbol+source combination
- **Cooling Period**: 60-minute wait after closing before reopening
- **Proper Cleanup**: Original BUY positions marked as `is_manually_closed=True`

### Database Schema

The Trading Service works with a deal tracking table that stores:

- **Identification**: Unique ID, creation timestamp, exchange order ID
- **Trade Details**: Symbol, quantity, execution price
- **Risk Management**: Take profit and stop loss price levels (for BUY orders)
- **Execution Status**: Flags indicating if TP/SL were triggered or position manually closed
- **Classification**: Action type (BUY/SELL) and originating strategy source

### Risk Management Features

1. **Dynamic SL/TP**: Based on market volatility (ATR calculations)
2. **Position Isolation**: Each symbol+source combination is independent
3. **Transaction Safety**: Full rollback on errors
4. **Duplicate Prevention**: Multiple layers of protection
5. **Cooling Periods**: Prevents rapid open/close cycles

## 📈 Adding New Strategies

To add a new trading strategy:

1. Create a new directory under `src/producers/`
2. Implement the strategy interface
3. Add configuration to `docker-compose.yaml`
4. Create a Dockerfile in `docker/producers/`

## 📦 Dependency Management

This project uses `pyproject.toml` for dependency management instead of `requirements/*.in` files.

### Available dependency groups:

- **core** (base dependencies): Installed by default with `pip install -e .`
- **consumer**: Database and messaging dependencies for the consumer service
- **producer**: Data analysis dependencies for producer services
- **migrator**: Database migration dependencies
- **scheduler**: Task scheduling dependencies
- **dev**: All development tools (testing, linting, formatting)

### Quick Start

```bash
# Install base dependencies
uv pip install -e .

# Install for development (includes all tools)
uv pip install -e ".[dev]"

# Install for specific service
uv pip install -e ".[consumer]"
uv pip install -e ".[producer]"

# Install multiple groups
uv pip install -e ".[consumer,producer]"
```
