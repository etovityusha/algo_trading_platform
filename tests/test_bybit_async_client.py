from decimal import Decimal

import pytest

from src.core.clients.bybit_async import BybitAsyncClient


def test_generate_signature_is_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    client = BybitAsyncClient(api_key="k", api_secret="s", is_demo=True)

    # Fixed timestamp for reproducibility
    ts = 1700000000000

    sig1 = client._generate_signature(params={"a": 1}, timestamp=ts)
    sig2 = client._generate_signature(params={"a": 1}, timestamp=ts)
    assert sig1 == sig2
    assert isinstance(sig1, str) and len(sig1) == 64


def test_calculate_stop_and_take_profit_prices() -> None:
    client = BybitAsyncClient(api_key="k", api_secret="s", is_demo=True)
    price = Decimal("100")

    sl = client._calculate_stop_loss_price(price, 1.0)
    tp = client._calculate_take_profit_price(price, 2.0)

    # With USDT precision 0.01
    assert sl == Decimal("99.00")
    assert tp == Decimal("102.00")


@pytest.mark.asyncio
async def test_buy_uses_instrument_precision_and_builds_order_and_parses_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = BybitAsyncClient(api_key="k", api_secret="s", is_demo=True)

    async def fake_get_instrument_info(symbol: str) -> dict:
        return {"lotSizeFilter": {"basePrecision": "0.0001"}}

    async def fake_get_ticker_price(symbol: str) -> Decimal:
        return Decimal("100")

    async def fake_request(method: str, endpoint: str, params: dict | None = None) -> dict:
        assert method == "POST"
        assert endpoint == "/v5/order/create"
        assert params is not None
        assert params["category"] == "spot"
        assert params["symbol"] == "BTCUSDT"
        assert params["side"] == "Buy"
        assert params["orderType"] == "Limit"
        # qty should be 1.0000 with base precision 0.0001
        assert params["qty"] == "1.0000"
        return {"result": {"orderId": "abc123"}}

    monkeypatch.setattr(client, "get_instrument_info", fake_get_instrument_info)
    monkeypatch.setattr(client, "get_ticker_price", fake_get_ticker_price)
    monkeypatch.setattr(client, "_request", fake_request)

    response = await client.buy(
        symbol="BTCUSDT",
        usdt_amount=Decimal("100"),
        stop_loss_percent=1.0,
        take_profit_percent=2.0,
    )

    assert response.order_id == "abc123"
    assert response.symbol == "BTCUSDT"
    assert response.qty == Decimal("1.0000")
    assert response.price == Decimal("100")


@pytest.mark.asyncio
async def test_get_candles_parses_response(monkeypatch: pytest.MonkeyPatch) -> None:
    client = BybitAsyncClient(api_key="k", api_secret="s", is_demo=True)

    async def fake_request(method: str, endpoint: str, params: dict | None = None) -> dict:
        assert method == "GET"
        assert endpoint.startswith("/v5/market/kline")
        return {
            "result": {
                "list": [
                    ["1700000000000", "100", "110", "90", "105", "1000"],
                    ["1700000001000", "105", "115", "95", "110", "2000"],
                ]
            }
        }

    monkeypatch.setattr(client, "_request", fake_request)

    candles = await client.get_candles("BTCUSDT", interval="15", limit=2)
    assert len(candles) == 2
    assert candles[0].open == Decimal("100")
    assert candles[1].close == Decimal("110")


@pytest.mark.asyncio
async def test_get_ticker_price_parses_last_price(monkeypatch: pytest.MonkeyPatch) -> None:
    client = BybitAsyncClient(api_key="k", api_secret="s", is_demo=True)

    async def fake_request(method: str, endpoint: str, params: dict | None = None) -> dict:
        assert method == "GET"
        assert endpoint == "/v5/market/tickers"
        return {
            "result": {
                "list": [
                    {"lastPrice": "100.1"},
                    {"lastPrice": "101.2"},
                ]
            }
        }

    monkeypatch.setattr(client, "_request", fake_request)

    price = await client.get_ticker_price("BTCUSDT")
    assert price == Decimal("101.2")


@pytest.mark.asyncio
async def test_stub_write_client_buy(monkeypatch: pytest.MonkeyPatch) -> None:

    async def fake_get_ticker_price(symbol: str) -> Decimal:
        return Decimal("100")

    from src.core.clients.bybit_async import BybitStubWriteClient

    stub = BybitStubWriteClient(api_key="k", api_secret="s", is_demo=True)
    monkeypatch.setattr(stub, "get_ticker_price", fake_get_ticker_price)

    resp = await stub.buy(
        symbol="BTCUSDT",
        usdt_amount=Decimal("50"),
        stop_loss_percent=1.0,
        take_profit_percent=2.0,
    )

    assert resp.symbol == "BTCUSDT"
    assert resp.price == Decimal("100")
    assert resp.qty == Decimal("50")  # stub returns usdt_amount as qty
    assert resp.order_id is not None and isinstance(resp.order_id, str)
