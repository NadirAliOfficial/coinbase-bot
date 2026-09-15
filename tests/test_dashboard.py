import os

import pytest

from src.config import Config
from src.dashboard import _todays_pnl, create_app
from src.market_state import MarketState
from src.positions import PositionStore


class FakePriceClient:
    def __init__(self, prices, balance=None):
        self.prices = prices
        self.balance = balance

    def get_current_price(self, product_id):
        return self.prices[product_id]

    def list_tradable_products(self, quote_currencies):
        return ["BTC-USD", "ETH-USD"]

    def get_usd_balance(self):
        return self.balance


@pytest.fixture
def store(tmp_path):
    return PositionStore(os.path.join(tmp_path, "test.db"))


def test_index_renders_with_no_data(store):
    app = create_app(store, client=None, config=Config())
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Coinbase Bot" in resp.data
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


def test_index_shows_account_balance(store):
    fake_client = FakePriceClient({}, balance=48.75)
    app = create_app(store, client=fake_client, config=Config())
    resp = app.test_client().get("/")

    assert b"48.75" in resp.data
    assert b"below" in resp.data  # 48.75 < default $100 position size


def test_index_shows_dash_when_balance_unavailable(store):
    app = create_app(store, client=None, config=Config())
    resp = app.test_client().get("/")

    assert b"unable to fetch balance" in resp.data


def test_todays_pnl_only_counts_trades_closed_today():
    import datetime as dt
    import time

    today_ts = int(time.time())
    yesterday_ts = int((dt.datetime.now() - dt.timedelta(days=1)).timestamp())

    closed = [
        {"exit_time": today_ts, "pnl_usd": 8.0},
        {"exit_time": yesterday_ts, "pnl_usd": 100.0},
    ]
    total, count = _todays_pnl(closed)
    assert count == 1
    assert total == 8.0


def test_dashboard_open_without_auth_configured(store):
    app = create_app(store, client=None, config=Config())
    resp = app.test_client().get("/")
    assert resp.status_code == 200


def test_dashboard_requires_auth_when_configured(store):
    cfg = Config()
    cfg.dashboard_user = "amery"
    cfg.dashboard_password = "secret123"
    app = create_app(store, client=None, config=cfg)
    client = app.test_client()

    resp = client.get("/")
    assert resp.status_code == 401

    import base64
    creds = base64.b64encode(b"amery:secret123").decode()
    resp = client.get("/", headers={"Authorization": f"Basic {creds}"})
    assert resp.status_code == 200

    bad_creds = base64.b64encode(b"amery:wrong").decode()
    resp = client.get("/", headers={"Authorization": f"Basic {bad_creds}"})
    assert resp.status_code == 401


def test_top_movers_render_with_market_state(store):
    market_state = MarketState()
    market_state.update(
        top_movers=[
            {"product_id": "BTC-USD", "pct_change": 16.5, "is_pump": True, "last_close": 80000.0},
            {"product_id": "ETH-USD", "pct_change": 3.2, "is_pump": False, "last_close": 3000.0},
        ],
        products_scanned=808,
        scan_seconds=12.4,
    )
    app = create_app(store, client=None, config=Config(), market_state=market_state)
    resp = app.test_client().get("/")

    assert b"BTC" in resp.data
    assert b"808 products scanned" in resp.data


def test_top_movers_empty_state_without_market_state(store):
    app = create_app(store, client=None, config=Config(), market_state=None)
    resp = app.test_client().get("/")
    assert b"No market data yet" in resp.data
