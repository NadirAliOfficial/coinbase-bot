from src.risk import (
    pnl_pct,
    pnl_usd,
    should_stop_loss,
    should_take_profit,
    stop_loss_price,
    take_profit_price,
)


def test_take_profit_price():
    assert take_profit_price(100.0, 8) == 108.0


def test_stop_loss_price():
    assert stop_loss_price(100.0, 3) == 97.0


def test_should_take_profit_true_at_threshold():
    assert should_take_profit(108.0, 100.0, 8) is True


def test_should_take_profit_false_below_threshold():
    assert should_take_profit(107.0, 100.0, 8) is False


def test_should_stop_loss_true_at_threshold():
    assert should_stop_loss(97.0, 100.0, 3) is True


def test_should_stop_loss_false_above_threshold():
    assert should_stop_loss(98.0, 100.0, 3) is False


def test_pnl_usd_and_pct():
    assert pnl_usd(100.0, 108.0, 10) == 80.0
    assert pnl_pct(100.0, 108.0) == 8.0
