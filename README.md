# Algorithmic Trading System

This project is a microservice-based algorithmic trading system that interacts with the Bybit cryptocurrency exchange. It consists of multiple producers that generate trading signals and a consumer that executes trades based on these signals.

## 🏗️ Architecture

The system consists of the following main components:

- **Producers**: Microservices that generate trading signals based on different strategies
  - `trand`: A trend-following strategy implementation
- **Consumer**: Service that processes trading signals and executes trades on Bybit
- **RabbitMQ**: Message broker for communication between producers and consumer
- **PostgreSQL**: Database for storing trade history and system state


## 📈 Adding New Strategies

To add a new trading strategy:

1. Create a new directory under `src/producers/`
2. Implement the strategy interface
3. Add configuration to `docker-compose.yaml`
4. Create a Dockerfile in `docker/producers/`

