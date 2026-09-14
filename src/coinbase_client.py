import time
import uuid
from typing import List, Optional

from coinbase.rest import RESTClient

from .logger import get_logger

logger = get_logger(__name__)


class Candle:
    def __init__(self, start: int, close: float):
        self.start = start
        self.close = close


class CoinbaseClient:
    def __init__(self, api_key: str, api_secret: str):
        self._client = RESTClient(api_key=api_key, api_secret=api_secret)

    def list_tradable_products(self, quote_currencies: tuple) -> List[str]:
        resp = self._client.get_products(product_type="SPOT")
        products = resp.get("products", []) if isinstance(resp, dict) else resp.products
        product_ids = []
        for p in products:
            quote = p.get("quote_currency_id") if isinstance(p, dict) else p.quote_currency_id
            disabled = p.get("trading_disabled") if isinstance(p, dict) else p.trading_disabled
            product_id = p.get("product_id") if isinstance(p, dict) else p.product_id
            if quote in quote_currencies and not disabled:
                product_ids.append(product_id)
        return product_ids

    def get_recent_closes(self, product_id: str, minutes: int) -> List[Candle]:
        end = int(time.time())
        start = end - (minutes + 1) * 60
        resp = self._client.get_candles(
            product_id=product_id,
            start=str(start),
            end=str(end),
            granularity="ONE_MINUTE",
        )
        candles = resp.get("candles", []) if isinstance(resp, dict) else resp.candles
        result = []
        for c in candles:
            c_start = int(c.get("start")) if isinstance(c, dict) else int(c.start)
            c_close = float(c.get("close")) if isinstance(c, dict) else float(c.close)
            result.append(Candle(c_start, c_close))
        result.sort(key=lambda c: c.start)
        return result

    def get_current_price(self, product_id: str) -> float:
        resp = self._client.get_product(product_id=product_id)
        price = resp.get("price") if isinstance(resp, dict) else resp.price
        return float(price)

    def market_buy(self, product_id: str, usd_amount: float) -> str:
        order_id = str(uuid.uuid4())
        self._client.market_order_buy(
            client_order_id=order_id,
            product_id=product_id,
            quote_size=f"{usd_amount:.2f}",
        )
        logger.info(f"BUY placed {product_id} usd={usd_amount:.2f} order_id={order_id}")
        return order_id

    def market_sell(self, product_id: str, base_size: float) -> str:
        order_id = str(uuid.uuid4())
        self._client.market_order_sell(
            client_order_id=order_id,
            product_id=product_id,
            base_size=f"{base_size:.8f}",
        )
        logger.info(f"SELL placed {product_id} qty={base_size:.8f} order_id={order_id}")
        return order_id

    def get_usd_balance(self) -> Optional[float]:
        resp = self._client.get_accounts()
        accounts = resp.get("accounts", []) if isinstance(resp, dict) else resp.accounts
        for a in accounts:
            currency = a.get("currency") if isinstance(a, dict) else a.currency
            if currency == "USD":
                bal = a.get("available_balance", {}) if isinstance(a, dict) else a.available_balance
                value = bal.get("value") if isinstance(bal, dict) else bal.value
                return float(value)
        return None
