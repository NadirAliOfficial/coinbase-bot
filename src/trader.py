from .config import Config
from .logger import get_logger
from .positions import PositionStore
from .risk import should_stop_loss, should_take_profit
from .scanner import detect_pump

logger = get_logger(__name__)


class Trader:
    def __init__(self, client, config: Config, store: PositionStore):
        self.client = client
        self.config = config
        self.store = store

    def scan_and_buy(self) -> None:
        product_ids = self.client.list_tradable_products(self.config.quote_currencies)
        for product_id in product_ids:
            if self.store.has_open_position(product_id):
                continue

            try:
                candles = self.client.get_recent_closes(product_id, self.config.pump_window_minutes)
            except Exception as exc:
                logger.warning(f"failed to fetch candles for {product_id}: {exc}")
                continue

            is_pump, pct_change = detect_pump(
                candles, self.config.pump_window_minutes, self.config.pump_threshold_pct
            )
            if not is_pump:
                continue

            entry_price = candles[-1].close
            quantity = self.config.position_size_usd / entry_price

            logger.info(f"PUMP detected {product_id} +{pct_change:.2f}% -> buying ${self.config.position_size_usd:.2f}")

            if not self.config.dry_run:
                self.client.market_buy(product_id, self.config.position_size_usd)

            self.store.open_position(product_id, entry_price, quantity, self.config.position_size_usd)

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
        self.scan_and_buy()
