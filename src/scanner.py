from typing import List, Tuple

from .coinbase_client import Candle


def detect_pump(candles: List[Candle], window_minutes: int, threshold_pct: float) -> Tuple[bool, float]:
    if len(candles) < 2:
        return False, 0.0

    latest = candles[-1]
    window_start_ts = latest.start - window_minutes * 60

    baseline = None
    for c in candles:
        if c.start <= window_start_ts:
            baseline = c
        else:
            break

    if baseline is None:
        baseline = candles[0]

    if baseline.close <= 0:
        return False, 0.0

    pct_change = ((latest.close - baseline.close) / baseline.close) * 100
    return pct_change >= threshold_pct, pct_change
