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

## ⚙️ Updating dependencies (requirements) with uv

When any `requirements/*.in` files change, recompile the corresponding `requirements/*.txt` files using uv.

Compile each .in to its .txt:

```bash
uv pip compile requirements/core.in -o requirements/core.txt
uv pip compile requirements/consumer.in -o requirements/consumer.txt
uv pip compile requirements/producer.in -o requirements/producer.txt
uv pip compile requirements/migrator.in -o requirements/migrator.txt
uv pip compile requirements/dev.in -o requirements/dev.txt
```

Compile all at once (bash):

```bash
for f in requirements/*.in; do \
  uv pip compile "$f" -o "requirements/$(basename "$f" .in).txt"; \
done
```
