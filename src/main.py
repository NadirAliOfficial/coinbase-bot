import threading
import time

from .coinbase_client import CoinbaseClient
from .config import Config
from .dashboard import create_app
from .logger import get_logger
from .positions import PositionStore
from .trader import Trader

logger = get_logger(__name__)


def main():
    config = Config()
    store = PositionStore(config.db_path)
    client = CoinbaseClient(config.api_key, config.api_secret)
    trader = Trader(client, config, store)

    if config.dry_run:
        logger.info("Starting in DRY_RUN mode - no live orders will be placed")
    else:
        logger.info("Starting in LIVE mode - real orders will be placed")

    app = create_app(store, client, config)
    dashboard_thread = threading.Thread(
        target=lambda: app.run(host=config.dashboard_host, port=config.dashboard_port, use_reloader=False),
        daemon=True,
    )
    dashboard_thread.start()
    logger.info(f"Dashboard running on http://{config.dashboard_host}:{config.dashboard_port}")

    while True:
        try:
            trader.run_cycle()
        except Exception as exc:
            logger.error(f"cycle failed: {exc}")
        time.sleep(config.poll_interval_seconds)


if __name__ == "__main__":
    main()
