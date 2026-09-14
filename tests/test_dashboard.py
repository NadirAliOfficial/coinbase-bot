import os

import pytest

from src.config import Config
from src.dashboard import create_app
from src.positions import PositionStore


class FakePriceClient:
    def __init__(self, prices):
        self.prices = prices

    def get_current_price(self, product_id):
        return self.prices[product_id]

    def list_tradable_products(self, quote_currencies):
        return ["BTC-USD", "ETH-USD"]


@pytest.fixture
def store(tmp_path):
    return PositionStore(os.path.join(tmp_path, "test.db"))


def test_index_renders_with_no_data(store):
    app = create_app(store, client=None, config=Config())
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Coinbase Momentum Bot" in resp.data
    assert b"No open positions" in resp.data
    assert b"No closed trades yet" in resp.data


def test_index_renders_open_and_closed_positions(store):
    store.open_position("BTC-USD", 100.0, 1.0, 100.0)
    pid = store.open_position("ETH-USD", 50.0, 2.0, 100.0)
    store.close_position(pid, 54.0, "take_profit")

    fake_client = FakePriceClient({"BTC-USD": 108.0})
    app = create_app(store, client=fake_client, config=Config())
    resp = app.test_client().get("/")

    assert resp.status_code == 200
    assert b"BTC" in resp.data
    assert b"ETH" in resp.data
    assert b"Take profit" in resp.data


def test_api_render_returns_fragments(store):
    store.open_position("SOL-USD", 20.0, 5.0, 100.0)
    app = create_app(store, client=None, config=Config())
    resp = app.test_client().get("/api/render")

    data = resp.get_json()
    assert "stats_html" in data
    assert "SOL" in data["open_table_html"]


def test_api_positions_unchanged(store):
    store.open_position("SOL-USD", 20.0, 5.0, 100.0)
    app = create_app(store, client=None, config=Config())
    resp = app.test_client().get("/api/positions")

    data = resp.get_json()
    assert len(data["open"]) == 1
    assert data["open"][0]["product_id"] == "SOL-USD"
