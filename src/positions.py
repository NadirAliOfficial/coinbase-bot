import sqlite3
import threading
import time
from typing import List, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    entry_price REAL NOT NULL,
    quantity REAL NOT NULL,
    usd_size REAL NOT NULL,
    entry_time INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    exit_price REAL,
    exit_time INTEGER,
    exit_reason TEXT,
    pnl_usd REAL,
    pnl_pct REAL
)
"""


class PositionStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.Lock()
        conn = self._connect()
        conn.execute(SCHEMA)
        conn.commit()
        conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def has_open_position(self, product_id: str) -> bool:
        with self._lock:
            conn = self._connect()
            row = conn.execute(
                "SELECT 1 FROM positions WHERE product_id = ? AND status = 'open'", (product_id,)
            ).fetchone()
            conn.close()
            return row is not None

    def open_position(self, product_id: str, entry_price: float, quantity: float, usd_size: float) -> int:
        with self._lock:
            conn = self._connect()
            cur = conn.execute(
                "INSERT INTO positions (product_id, entry_price, quantity, usd_size, entry_time, status) "
                "VALUES (?, ?, ?, ?, ?, 'open')",
                (product_id, entry_price, quantity, usd_size, int(time.time())),
            )
            conn.commit()
            position_id = cur.lastrowid
            conn.close()
            return position_id

    def close_position(self, position_id: int, exit_price: float, exit_reason: str) -> None:
        with self._lock:
            conn = self._connect()
            row = conn.execute("SELECT entry_price, quantity FROM positions WHERE id = ?", (position_id,)).fetchone()
            entry_price = row["entry_price"]
            quantity = row["quantity"]
            pnl_usd = (exit_price - entry_price) * quantity
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            conn.execute(
                "UPDATE positions SET status = 'closed', exit_price = ?, exit_time = ?, "
                "exit_reason = ?, pnl_usd = ?, pnl_pct = ? WHERE id = ?",
                (exit_price, int(time.time()), exit_reason, pnl_usd, pnl_pct, position_id),
            )
            conn.commit()
            conn.close()

    def get_open_positions(self) -> List[sqlite3.Row]:
        with self._lock:
            conn = self._connect()
            rows = conn.execute("SELECT * FROM positions WHERE status = 'open' ORDER BY entry_time DESC").fetchall()
            conn.close()
            return rows

    def get_closed_positions(self, limit: int = 100) -> List[sqlite3.Row]:
        with self._lock:
            conn = self._connect()
            rows = conn.execute(
                "SELECT * FROM positions WHERE status = 'closed' ORDER BY exit_time DESC LIMIT ?", (limit,)
            ).fetchall()
            conn.close()
            return rows

    def get_position(self, position_id: int) -> Optional[sqlite3.Row]:
        with self._lock:
            conn = self._connect()
            row = conn.execute("SELECT * FROM positions WHERE id = ?", (position_id,)).fetchone()
            conn.close()
            return row
