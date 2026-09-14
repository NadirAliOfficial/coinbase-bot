import os

import pytest

from src.positions import PositionStore


@pytest.fixture
def store(tmp_path):
    db_path = os.path.join(tmp_path, "test.db")
    return PositionStore(db_path)


def test_open_and_get_position(store):
    position_id = store.open_position("BTC-USD", 50000.0, 0.002, 100.0)
    assert store.has_open_position("BTC-USD") is True

    open_positions = store.get_open_positions()
    assert len(open_positions) == 1
    assert open_positions[0]["product_id"] == "BTC-USD"
    assert open_positions[0]["id"] == position_id


def test_close_position_computes_pnl(store):
    position_id = store.open_position("ETH-USD", 2000.0, 0.05, 100.0)
    store.close_position(position_id, 2160.0, "take_profit")

    assert store.has_open_position("ETH-USD") is False
    closed = store.get_closed_positions()
    assert len(closed) == 1
    assert closed[0]["exit_reason"] == "take_profit"
    assert closed[0]["pnl_usd"] == pytest.approx(8.0)
    assert closed[0]["pnl_pct"] == pytest.approx(8.0)


def test_no_duplicate_open_position_for_same_product(store):
    store.open_position("SOL-USD", 100.0, 1.0, 100.0)
    assert store.has_open_position("SOL-USD") is True
    assert store.has_open_position("DOGE-USD") is False
