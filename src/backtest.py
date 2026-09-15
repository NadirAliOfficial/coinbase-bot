import sys
import time

from .coinbase_client import CoinbaseClient
from .config import Config
from .risk import pnl_pct, pnl_usd, should_stop_loss, should_take_profit
from .scanner import detect_pump


def backtest_product(client, product_id, config, history_minutes):
    candles = client.get_recent_closes(product_id, history_minutes)
    if len(candles) < config.pump_window_minutes + 2:
        return [], 0

    trades = []
    signals = 0
    position = None

    for i in range(config.pump_window_minutes, len(candles)):
        current = candles[i]

        if position is not None:
            exit_reason = None
            if should_take_profit(current.close, position["entry_price"], config.take_profit_pct):
                exit_reason = "take_profit"
            elif should_stop_loss(current.close, position["entry_price"], config.stop_loss_pct):
                exit_reason = "stop_loss"

            if exit_reason:
                qty = config.position_size_usd / position["entry_price"]
                trades.append({
                    "product_id": product_id,
                    "entry_price": position["entry_price"],
                    "exit_price": current.close,
                    "exit_reason": exit_reason,
                    "pnl_usd": pnl_usd(position["entry_price"], current.close, qty),
                    "pnl_pct": pnl_pct(position["entry_price"], current.close),
                })
                position = None

        if position is None:
            window = candles[i - config.pump_window_minutes: i + 1]
            is_pump, _ = detect_pump(window, config.pump_window_minutes, config.pump_threshold_pct)
            if is_pump:
                signals += 1
                position = {"entry_price": current.close, "entry_time": current.start}

    still_open = position is not None
    return trades, signals, still_open


def main():
    config = Config()
    client = CoinbaseClient(config.api_key, config.api_secret)
    history_minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 300

    print(f"Fetching tradable {'/'.join(config.quote_currencies)} products...")
    products = client.list_tradable_products(config.quote_currencies)
    print(f"{len(products)} products to scan. History window: {history_minutes} minutes.\n")

    live_movers = []
    all_trades = []
    products_with_signal = 0
    still_open_count = 0
    errors = 0

    start = time.time()
    for idx, product_id in enumerate(products, 1):
        try:
            candles = client.get_recent_closes(product_id, config.pump_window_minutes)
            is_pump, pct = detect_pump(candles, config.pump_window_minutes, config.pump_threshold_pct)
            if candles:
                live_movers.append((product_id, pct))
        except Exception:
            pass

        try:
            trades, signals, still_open = backtest_product(client, product_id, config, history_minutes)
            if signals > 0:
                products_with_signal += 1
            if still_open:
                still_open_count += 1
            all_trades.extend(trades)
        except Exception:
            errors += 1

        if idx % 100 == 0:
            elapsed = time.time() - start
            print(f"  scanned {idx}/{len(products)} ({elapsed:.0f}s elapsed)")

    elapsed = time.time() - start
    print(f"\nScan complete in {elapsed:.0f}s ({errors} products failed to fetch).\n")

    print("=" * 60)
    print("LIVE CANDIDATES (right now)")
    print("=" * 60)
    live_movers.sort(key=lambda x: x[1], reverse=True)
    triggered = [m for m in live_movers if m[1] >= config.pump_threshold_pct]
    print(f"Products currently meeting the +{config.pump_threshold_pct:.0f}%/{config.pump_window_minutes}m trigger: {len(triggered)}")
    for product_id, pct in triggered:
        print(f"  BUY SIGNAL  {product_id:<12} {pct:+.2f}%")

    print(f"\nTop 15 movers right now (for context, most below threshold):")
    for product_id, pct in live_movers[:15]:
        print(f"  {product_id:<12} {pct:+.2f}%")

    print()
    print("=" * 60)
    print(f"BACKTEST (last {history_minutes} minutes, simulated, no real orders)")
    print("=" * 60)
    print(f"Products with at least one pump signal: {products_with_signal}")
    print(f"Positions still open at end of window: {still_open_count}")
    print(f"Total simulated trades closed: {len(all_trades)}")

    if all_trades:
        wins = [t for t in all_trades if t["pnl_usd"] > 0]
        losses = [t for t in all_trades if t["pnl_usd"] <= 0]
        total_pnl = sum(t["pnl_usd"] for t in all_trades)
        win_rate = len(wins) / len(all_trades) * 100
        print(f"Wins: {len(wins)}  Losses: {len(losses)}  Win rate: {win_rate:.1f}%")
        print(f"Total simulated P&L: {'-' if total_pnl < 0 else ''}${abs(total_pnl):,.2f}")
        print(f"\nTrade log:")
        for t in sorted(all_trades, key=lambda t: t["pnl_usd"], reverse=True):
            sign = "-" if t["pnl_usd"] < 0 else ""
            print(
                f"  {t['product_id']:<12} {t['exit_reason']:<12} "
                f"entry={t['entry_price']:<14.6f} exit={t['exit_price']:<14.6f} "
                f"pnl={sign}${abs(t['pnl_usd']):.2f} ({t['pnl_pct']:+.2f}%)"
            )
    else:
        print("No trades triggered in this window — the +15%/15min threshold is rare by design.")


if __name__ == "__main__":
    main()
