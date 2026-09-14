# Coinbase Momentum Bot

Scans all Coinbase spot markets (USD/USDC pairs) for coins up 15% in the last
15 minutes, buys $100 worth, and exits at +8% take profit or -3% stop loss.
Includes a small web dashboard to track open and closed trades.

## Strategy

- Buy trigger: price up `PUMP_THRESHOLD_PCT` (default 15%) over `PUMP_WINDOW_MINUTES` (default 15 min)
- Take profit: `TAKE_PROFIT_PCT` (default 8%)
- Stop loss: `STOP_LOSS_PCT` (default 3%)
- Position size: `POSITION_SIZE_USD` per coin (default $100), multiple coins can be open at once
- Only one open position per product at a time

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and add your Coinbase Advanced Trade API key/secret. Create the
key with **trade-only** permission — do not enable withdrawals.

Leave `DRY_RUN=true` for your first run. In dry run, the bot scans real
market data and simulates buys/sells (writing them to the dashboard) without
placing real orders. Set `DRY_RUN=false` only once you've confirmed the
behavior looks right.

## Run

```bash
source .venv/bin/activate
python -m src.main
```

Dashboard: http://localhost:5000 (port configurable via `DASHBOARD_PORT`)

## Tests

```bash
source .venv/bin/activate
pytest
```

## Notes

- $100 positions are small relative to Coinbase trading fees/spread on some
  pairs — fees will eat into the 8% target more than on larger size.
- If multiple coins pump at once, each opens its own $100 position, so your
  account balance needs to cover `POSITION_SIZE_USD * number of simultaneous signals`.
- The bot polls on `POLL_INTERVAL_SECONDS` (default 60s), so entries/exits
  are not tick-perfect — a fast-moving coin can overshoot the exact 8%/-3%
  mark between polls.
