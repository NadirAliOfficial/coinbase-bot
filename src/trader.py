import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from .config import Config
from .logger import get_logger
from .positions import PositionStore
from .risk import should_stop_loss, should_take_profit
from .scanner import detect_pump

logger = get_logger(__name__)

TOP_MOVERS_LIMIT = 20


class RateLimiter:
    def __init__(self, max_per_second: float):
        self._interval = 1.0 / max_per_second
        self._lock = threading.Lock()
        self._next_slot = 0.0

    def wait(self):
        with self._lock:
            now = time.time()
            start = max(now, self._next_slot)
            self._next_slot = start + self._interval
            delay = start - now
        if delay > 0:
            time.sleep(delay)


class Trader:
    def __init__(self, client, config: Config, store: PositionStore, market_state=None):
        self.client = client
        self.config = config
        self.store = store
        self.market_state = market_state
        self._rate_limiter = RateLimiter(config.scan_rate_limit_per_second)

    def _fetch_one(self, product_id):
        candles = None
        for attempt in range(3):
            self._rate_limiter.wait()
            try:
                candles = self.client.get_recent_closes(product_id, self.config.pump_window_minutes)
                break
            except Exception:
                if attempt < 2:
                    time.sleep(0.5 * (attempt + 1))
        if not candles:
            return None

        is_pump, pct_change = detect_pump(candles, self.config.pump_window_minutes, self.config.pump_threshold_pct)
        return {
            "product_id": product_id,
            "pct_change": pct_change,
            "is_pump": is_pump,
            "last_close": candles[-1].close,
        }

    def scan_and_buy(self) -> int:
        start = time.time()
        product_ids = self.client.list_tradable_products(self.config.quote_currencies)

        results = []
        with ThreadPoolExecutor(max_workers=self.config.scan_concurrency) as pool:
            futures = {pool.submit(self._fetch_one, pid): pid for pid in product_ids}
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    results.append(result)

        for result in results:
            if not result["is_pump"]:
                continue
            product_id = result["product_id"]
            if self.store.has_open_position(product_id):
                continue

            entry_price = result["last_close"]
            quantity = self.config.position_size_usd / entry_price

            logger.info(
                f"PUMP detected {product_id} +{result['pct_change']:.2f}% -> buying ${self.config.position_size_usd:.2f}"
            )

            if not self.config.dry_run:
                self.client.market_buy(product_id, self.config.position_size_usd)

            self.store.open_position(product_id, entry_price, quantity, self.config.position_size_usd)

        if self.market_state is not None:
            # Coinbase lists most coins on both USD and USDC; show each base asset once
            # (keeping its best-performing pair) so the panel isn't full of duplicates.
            best_by_base = {}
            for r in results:
                base = r["product_id"].split("-")[0]
                if base not in best_by_base or r["pct_change"] > best_by_base[base]["pct_change"]:
                    best_by_base[base] = r

            top_movers = sorted(best_by_base.values(), key=lambda r: r["pct_change"], reverse=True)[:TOP_MOVERS_LIMIT]
            self.market_state.update(top_movers, len(product_ids), time.time() - start)

        return len(product_ids)

    def manage_open_positions(self) -> None:
        for position in self.store.get_open_positions():
            product_id = position["product_id"]
            entry_price = position["entry_price"]
            quantity = position["quantity"]

            try:
                current_price = self.client.get_current_price(product_id)
            except Exception as exc:
                logger.warning(f"failed to fetch price for {product_id}: {exc}")
                continue

            exit_reason = None
            if should_take_profit(current_price, entry_price, self.config.take_profit_pct):
                exit_reason = "take_profit"
            elif should_stop_loss(current_price, entry_price, self.config.stop_loss_pct):
                exit_reason = "stop_loss"

            if exit_reason is None:
                continue

            logger.info(f"{exit_reason.upper()} {product_id} entry={entry_price} exit={current_price}")

            if not self.config.dry_run:
                self.client.market_sell(product_id, quantity)

            self.store.close_position(position["id"], current_price, exit_reason)

    def run_cycle(self) -> None:
        self.manage_open_positions()
        scanned = self.scan_and_buy()
        open_count = len(self.store.get_open_positions())
        logger.info(f"cycle complete: scanned {scanned} products, {open_count} open position(s)")
