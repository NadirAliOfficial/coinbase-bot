import threading
import time

from .coinbase_client import CoinbaseClient
from .config import Config
from .dashboard import create_app
from .logger import get_logger
from .market_state import MarketState
from .positions import PositionStore
from .trader import Trader

logger = get_logger(__name__)


def _position_monitor_loop(trader: Trader, config: Config):
    while True:
        try:
            trader.manage_open_positions()
        except Exception as exc:
            logger.error(f"position monitor failed: {exc}")
        time.sleep(config.poll_interval_seconds)


def _market_scan_loop(trader: Trader):
    while True:
        try:
            scanned = trader.scan_and_buy()
            logger.info(f"scan complete: {scanned} products checked")
        except Exception as exc:
            logger.error(f"market scan failed: {exc}")


def main():
    config = Config()
    store = PositionStore(config.db_path)
    client = CoinbaseClient(config.api_key, config.api_secret)
    market_state = MarketState()
    trader = Trader(client, config, store, market_state)

    if config.dry_run:
        logger.info("Starting in DRY_RUN mode - no live orders will be placed")
    else:
        logger.info("Starting in LIVE mode - real orders will be placed")

    app = create_app(store, client, config, market_state)
    dashboard_thread = threading.Thread(
        target=lambda: app.run(host=config.dashboard_host, port=config.dashboard_port, use_reloader=False),
        daemon=True,
    )
    dashboard_thread.start()
    logger.info(f"Dashboard running on http://{config.dashboard_host}:{config.dashboard_port}")

    scan_thread = threading.Thread(target=_market_scan_loop, args=(trader,), daemon=True)
    scan_thread.start()

    _position_monitor_loop(trader, config)


if __name__ == "__main__":
    main()
