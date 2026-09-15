import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Config:
    api_key: str = field(default_factory=lambda: os.getenv("CB_API_KEY", ""))
    api_secret: str = field(default_factory=lambda: os.getenv("CB_API_SECRET", ""))
    dry_run: bool = field(default_factory=lambda: _bool("DRY_RUN", True))

    poll_interval_seconds: int = field(default_factory=lambda: int(os.getenv("POLL_INTERVAL_SECONDS", "60")))
    scan_concurrency: int = field(default_factory=lambda: int(os.getenv("SCAN_CONCURRENCY", "8")))
    pump_window_minutes: int = field(default_factory=lambda: int(os.getenv("PUMP_WINDOW_MINUTES", "15")))
    pump_threshold_pct: float = field(default_factory=lambda: float(os.getenv("PUMP_THRESHOLD_PCT", "15")))
    take_profit_pct: float = field(default_factory=lambda: float(os.getenv("TAKE_PROFIT_PCT", "8")))
    stop_loss_pct: float = field(default_factory=lambda: float(os.getenv("STOP_LOSS_PCT", "3")))
    position_size_usd: float = field(default_factory=lambda: float(os.getenv("POSITION_SIZE_USD", "100")))
    quote_currencies: tuple = field(
        default_factory=lambda: tuple(
            c.strip().upper() for c in os.getenv("QUOTE_CURRENCIES", "USD,USDC").split(",") if c.strip()
        )
    )

    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "positions.db"))
    dashboard_port: int = field(default_factory=lambda: int(os.getenv("DASHBOARD_PORT", "5000")))
    dashboard_host: str = field(default_factory=lambda: os.getenv("DASHBOARD_HOST", "127.0.0.1"))
    dashboard_user: str = field(default_factory=lambda: os.getenv("DASHBOARD_USER", ""))
    dashboard_password: str = field(default_factory=lambda: os.getenv("DASHBOARD_PASSWORD", ""))
