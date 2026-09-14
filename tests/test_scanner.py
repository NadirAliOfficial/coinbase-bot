from src.coinbase_client import Candle
from src.scanner import detect_pump


def make_candles(closes, start=1_000_000, step=60):
    return [Candle(start + i * step, c) for i, c in enumerate(closes)]


def test_detect_pump_triggers_on_15_percent_rise():
    closes = [100.0] * 15 + [116.0]
    candles = make_candles(closes)
    is_pump, pct = detect_pump(candles, window_minutes=15, threshold_pct=15.0)
    assert is_pump is True
    assert pct >= 15.0


def test_detect_pump_does_not_trigger_below_threshold():
    closes = [100.0] * 15 + [110.0]
    candles = make_candles(closes)
    is_pump, pct = detect_pump(candles, window_minutes=15, threshold_pct=15.0)
    assert is_pump is False
    assert pct < 15.0


def test_detect_pump_handles_falling_price():
    closes = [100.0] * 15 + [90.0]
    candles = make_candles(closes)
    is_pump, pct = detect_pump(candles, window_minutes=15, threshold_pct=15.0)
    assert is_pump is False
    assert pct < 0


def test_detect_pump_insufficient_data():
    candles = make_candles([100.0])
    is_pump, pct = detect_pump(candles, window_minutes=15, threshold_pct=15.0)
    assert is_pump is False
    assert pct == 0.0
