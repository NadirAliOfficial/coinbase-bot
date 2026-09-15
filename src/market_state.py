import threading
import time


class MarketState:
    def __init__(self):
        self._lock = threading.Lock()
        self._top_movers = []
        self._products_scanned = 0
        self._scan_seconds = None
        self._last_scan_at = None

    def update(self, top_movers, products_scanned, scan_seconds):
        with self._lock:
            self._top_movers = top_movers
            self._products_scanned = products_scanned
            self._scan_seconds = scan_seconds
            self._last_scan_at = time.time()

    def snapshot(self):
        with self._lock:
            return {
                "top_movers": list(self._top_movers),
                "products_scanned": self._products_scanned,
                "scan_seconds": self._scan_seconds,
                "last_scan_at": self._last_scan_at,
            }
