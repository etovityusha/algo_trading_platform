import datetime
import hashlib
import hmac
import json
import time
from decimal import ROUND_DOWN, Decimal
from typing import Any
from urllib.parse import urlencode

import aiohttp
from uuid_extensions import uuid7

from src.core.clients.dto import BuyResponse, Candle
from src.core.clients.interface import AbstractReadOnlyClient, AbstractWriteClient


class BybitAsyncClient(AbstractReadOnlyClient, AbstractWriteClient):
    def __init__(self, api_key: str, api_secret: str, is_demo: bool = True) -> None:
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = "https://api-testnet.bybit.com" if is_demo else "https://api.bybit.com"
        self._lot_precision = {
            "USDT": Decimal("0.01"),
        }

    async def __aenter__(self) -> "BybitAsyncClient":
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self._session.close()

    def _generate_signature(self, params: dict[str, Any] | str, timestamp: int) -> str:
        """Generate signature for authentication"""
        param_str = str(timestamp) + self._api_key + "5000" + str(params)
        hash = hmac.new(bytes(self._api_secret, "utf-8"), param_str.encode("utf-8"), hashlib.sha256)
        signature = hash.hexdigest()
        return signature

    async def get_candles(
        self, symbol: str, interval: str = "15", limit: int = 200, start: datetime.datetime | None = None
    ) -> list[Candle]:
        params = {
            "category": "spot",
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        if start is not None:
            params["start"] = int(start.timestamp() * 1000)
        response = await self._request(
            method="GET",
            endpoint="/v5/market/kline",
            params=params,
        )
        candles = [
            Candle(
                timestamp=int(candle[0]),  # timestamp at index 0
                open=Decimal(candle[1]),  # open at index 1
                high=Decimal(candle[2]),  # high at index 2
                low=Decimal(candle[3]),  # low at index 3
                close=Decimal(candle[4]),  # close at index 4
                volume=Decimal(candle[5]),  # volume at index 5
            )
            for candle in response["result"]["list"]
        ]
        return candles

    async def get_instrument_info(self, symbol: str) -> dict:
        """Get instrument information including lot size precision"""
        response = await self._request(
            method="GET",
            endpoint="/v5/market/instruments-info",
            params={"category": "spot", "symbol": symbol},
        )
        result: dict = response["result"]["list"][0]
        return result

    async def _request(self, method: str, endpoint: str, params: dict | None = None) -> dict[str, Any]:
        """Make authenticated request to Bybit API"""
        timestamp = int(time.time() * 1000)
        headers = {
            "Content-Type": "application/json",
            "X-BAPI-API-KEY": self._api_key,
            "X-BAPI-TIMESTAMP": str(timestamp),
            "X-BAPI-RECV-WINDOW": "5000",
        }

        # For GET requests, add params to URL
        if method == "GET":
            if params:
                query_string = urlencode(params)
                endpoint = f"{endpoint}?{query_string}"
            headers["X-BAPI-SIGN"] = self._generate_signature(params if params else "", timestamp)
        else:
            # For POST requests, sign the request body
            headers["X-BAPI-SIGN"] = self._generate_signature(json.dumps(params) if params else "", timestamp)

        url = f"{self._base_url}{endpoint}"
        async with self._session.request(
            method=method,
            url=url,
            headers=headers,
            json=params if method == "POST" else None,
        ) as response:
            return dict(await response.json())

    async def get_ticker_price(self, symbol: str) -> Decimal:
        """Get current ticker information"""
        response = await self._request(
            method="GET",
            endpoint="/v5/market/tickers",
            params={"category": "spot", "symbol": symbol},
        )
        return Decimal(response["result"]["list"][-1]["lastPrice"])

    async def buy(
        self,
        symbol: str,
        usdt_amount: Decimal,
        stop_loss_percent: float | None = None,
        take_profit_percent: float | None = None,
    ) -> BuyResponse:
        precision = self._lot_precision.get(symbol)
        if not precision:
            instrument_info = await self.get_instrument_info(symbol)
            precision = Decimal(instrument_info["lotSizeFilter"]["basePrecision"])
            self._lot_precision[symbol] = precision

        price: Decimal = await self.get_ticker_price(symbol)
        amount = (usdt_amount / price).quantize(precision, rounding=ROUND_DOWN)
        order_params = {
            "category": "spot",
            "symbol": symbol,
            "side": "Buy",
            "orderType": "Limit",
            "qty": str(amount),
            "price": str(price),
            "timeInForce": "GTC",
        }

        stop_price: Decimal | None = None
        if stop_loss_percent:
            stop_price = self._calculate_stop_loss_price(price, stop_loss_percent)
            order_params["stopLoss"] = str(stop_price)
            order_params["slTriggerBy"] = "LastPrice"
            order_params["slOrderType"] = "Market"

        take_profit_price: Decimal | None = None
        if take_profit_percent:
            take_profit_price = self._calculate_take_profit_price(price, take_profit_percent)
            order_params["takeProfit"] = str(take_profit_price)
            order_params["tpTriggerBy"] = "LastPrice"
            order_params["tpOrderType"] = "Market"

        response = await self._request(method="POST", endpoint="/v5/order/create", params=order_params)
        order_id = response.get("result", {}).get("orderId")
        return BuyResponse(
            order_id=order_id,
            symbol=symbol,
            qty=amount,
            price=price,
            stop_loss_price=stop_price,
            take_profit_price=take_profit_price,
        )

    def _calculate_stop_loss_price(self, price: Decimal, stop_loss_percent: float) -> Decimal:
        return (price * (1 - Decimal(stop_loss_percent) / 100)).quantize(
            self._lot_precision["USDT"], rounding=ROUND_DOWN
        )

    def _calculate_take_profit_price(self, price: Decimal, take_profit_percent: float) -> Decimal:
        return (price * (1 + Decimal(take_profit_percent) / 100)).quantize(
            self._lot_precision["USDT"], rounding=ROUND_DOWN
        )


class BybitStubWriteClient(BybitAsyncClient):
    """Same as BybitAsyncClient, but overrides write methods to return fake responses"""

    async def buy(
        self,
        symbol: str,
        usdt_amount: Decimal,
        stop_loss_percent: float | None = None,
        take_profit_percent: float | None = None,
    ) -> BuyResponse:
        price = await self.get_ticker_price(symbol)
        return BuyResponse(
            order_id=uuid7(as_type="str"),
            symbol=symbol,
            qty=usdt_amount,
            price=price,
            stop_loss_price=(self._calculate_stop_loss_price(price, stop_loss_percent) if stop_loss_percent else None),
            take_profit_price=(
                self._calculate_take_profit_price(price, take_profit_percent) if take_profit_percent else None
            ),
        )
