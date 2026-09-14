import os

import pytest

from src.coinbase_client import Candle
from src.config import Config
from src.positions import PositionStore
from src.trader import Trader


class FakeClient:
    def __init__(self, prices, candles):
        self.prices = prices
        self.candles = candles
        self.buys = []
        self.sells = []

    def list_tradable_products(self, quote_currencies):
        return list(self.candles.keys())

    def get_recent_closes(self, product_id, minutes):
        return self.candles[product_id]

    def get_current_price(self, product_id):
        return self.prices[product_id]

    def market_buy(self, product_id, usd_amount):
        self.buys.append((product_id, usd_amount))
        return "buy-order"

    def market_sell(self, product_id, base_size):
        self.sells.append((product_id, base_size))
        return "sell-order"


def make_candles(closes, start=1_000_000, step=60):
    return [Candle(start + i * step, c) for i, c in enumerate(closes)]


@pytest.fixture
def config(tmp_path):
    cfg = Config()
    cfg.dry_run = True
    cfg.db_path = os.path.join(tmp_path, "test.db")
    cfg.pump_window_minutes = 15
    cfg.pump_threshold_pct = 15.0
    cfg.take_profit_pct = 8.0
    cfg.stop_loss_pct = 3.0
    cfg.position_size_usd = 100.0
    cfg.quote_currencies = ("USD",)
    return cfg


def test_scan_and_buy_opens_position_on_pump(config):
    store = PositionStore(config.db_path)
    candles = {"BTC-USD": make_candles([100.0] * 15 + [120.0])}
    client = FakeClient(prices={}, candles=candles)
    trader = Trader(client, config, store)

    trader.scan_and_buy()

    assert store.has_open_position("BTC-USD") is True
    assert client.buys == []  # dry run: no live order placed


def test_scan_and_buy_skips_existing_position(config):
    store = PositionStore(config.db_path)
    candles = {"BTC-USD": make_candles([100.0] * 15 + [120.0])}
    client = FakeClient(prices={}, candles=candles)
    trader = Trader(client, config, store)

    trader.scan_and_buy()
    first_count = len(store.get_open_positions())
    trader.scan_and_buy()
    second_count = len(store.get_open_positions())

    assert first_count == 1
    assert second_count == 1


def test_manage_open_positions_closes_on_take_profit(config):
    store = PositionStore(config.db_path)
    store.open_position("BTC-USD", 100.0, 1.0, 100.0)
    client = FakeClient(prices={"BTC-USD": 109.0}, candles={})
    trader = Trader(client, config, store)

    trader.manage_open_positions()

    assert store.has_open_position("BTC-USD") is False
    closed = store.get_closed_positions()
    assert closed[0]["exit_reason"] == "take_profit"


def test_manage_open_positions_closes_on_stop_loss(config):
    store = PositionStore(config.db_path)
    store.open_position("ETH-USD", 100.0, 1.0, 100.0)
    client = FakeClient(prices={"ETH-USD": 96.0}, candles={})
    trader = Trader(client, config, store)

    trader.manage_open_positions()

    assert store.has_open_position("ETH-USD") is False
    closed = store.get_closed_positions()
    assert closed[0]["exit_reason"] == "stop_loss"


def test_manage_open_positions_holds_when_within_range(config):
    store = PositionStore(config.db_path)
    store.open_position("SOL-USD", 100.0, 1.0, 100.0)
    client = FakeClient(prices={"SOL-USD": 102.0}, candles={})
    trader = Trader(client, config, store)

    trader.manage_open_positions()

    assert store.has_open_position("SOL-USD") is True
