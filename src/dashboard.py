from flask import Flask, jsonify, render_template_string

from .positions import PositionStore

TEMPLATE = """
<!doctype html>
<html>
<head>
  <title>Coinbase Momentum Bot</title>
  <meta http-equiv="refresh" content="10">
  <style>
    body { font-family: -apple-system, Arial, sans-serif; margin: 24px; background: #0f1115; color: #e6e6e6; }
    h1 { font-size: 20px; }
    table { border-collapse: collapse; width: 100%; margin-bottom: 32px; }
    th, td { padding: 8px 12px; border-bottom: 1px solid #2a2d34; text-align: left; font-size: 14px; }
    th { color: #9aa0a6; }
    .pos { color: #35c46b; }
    .neg { color: #e5484d; }
    .summary { display: flex; gap: 24px; margin-bottom: 20px; }
    .card { background: #16181d; padding: 12px 16px; border-radius: 8px; }
    .card .label { color: #9aa0a6; font-size: 12px; }
    .card .value { font-size: 18px; font-weight: 600; }
  </style>
</head>
<body>
  <h1>Coinbase Momentum Bot</h1>

  <div class="summary">
    <div class="card"><div class="label">Open Positions</div><div class="value">{{ open_positions|length }}</div></div>
    <div class="card"><div class="label">Closed Trades</div><div class="value">{{ closed_positions|length }}</div></div>
    <div class="card"><div class="label">Total P&L</div><div class="value {{ 'pos' if total_pnl >= 0 else 'neg' }}">${{ '%.2f'|format(total_pnl) }}</div></div>
  </div>

  <h2>Open Positions</h2>
  <table>
    <tr><th>Product</th><th>Entry Price</th><th>Quantity</th><th>USD Size</th><th>Entry Time</th></tr>
    {% for p in open_positions %}
    <tr>
      <td>{{ p.product_id }}</td>
      <td>{{ '%.6f'|format(p.entry_price) }}</td>
      <td>{{ '%.6f'|format(p.quantity) }}</td>
      <td>${{ '%.2f'|format(p.usd_size) }}</td>
      <td>{{ p.entry_time }}</td>
    </tr>
    {% endfor %}
  </table>

  <h2>Closed Trades</h2>
  <table>
    <tr><th>Product</th><th>Entry</th><th>Exit</th><th>Reason</th><th>P&L $</th><th>P&L %</th></tr>
    {% for p in closed_positions %}
    <tr>
      <td>{{ p.product_id }}</td>
      <td>{{ '%.6f'|format(p.entry_price) }}</td>
      <td>{{ '%.6f'|format(p.exit_price) }}</td>
      <td>{{ p.exit_reason }}</td>
      <td class="{{ 'pos' if p.pnl_usd >= 0 else 'neg' }}">${{ '%.2f'|format(p.pnl_usd) }}</td>
      <td class="{{ 'pos' if p.pnl_pct >= 0 else 'neg' }}">{{ '%.2f'|format(p.pnl_pct) }}%</td>
    </tr>
    {% endfor %}
  </table>
</body>
</html>
"""


def create_app(store: PositionStore) -> Flask:
    app = Flask(__name__)

    @app.route("/")
    def index():
        open_positions = store.get_open_positions()
        closed_positions = store.get_closed_positions()
        total_pnl = sum(p["pnl_usd"] or 0 for p in closed_positions)
        return render_template_string(
            TEMPLATE,
            open_positions=open_positions,
            closed_positions=closed_positions,
            total_pnl=total_pnl,
        )

    @app.route("/api/positions")
    def api_positions():
        return jsonify(
            {
                "open": [dict(p) for p in store.get_open_positions()],
                "closed": [dict(p) for p in store.get_closed_positions()],
            }
        )

    return app
