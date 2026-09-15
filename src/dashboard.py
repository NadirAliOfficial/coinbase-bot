import datetime as dt
import hmac

from flask import Flask, jsonify, render_template_string, request, Response

from .config import Config
from .positions import PositionStore


def _fmt_usd(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.2f}"


PAGE = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <title>Coinbase Bot</title>
  <script>
    (function () {
      try {
        var stored = localStorage.getItem('cmb-theme');
        document.documentElement.setAttribute('data-theme', stored || 'dark');
      } catch (e) {}
    })();
  </script>
  <link rel="icon" type="image/png" href="/static/logo.png">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,500,1,0&display=swap" rel="stylesheet">
  <style>
    :root {
      --paper: #f7f4ee;
      --paper-alt: #fffdf9;
      --ink: #1c1b18;
      --ink-dim: #7a7669;
      --ink-faint: #a8a396;
      --hairline: #ddd8cb;
      --periwinkle: #6674b8;
      --periwinkle-bg: rgba(102,116,184,0.12);
      --tan: #c98a4b;
      --tan-bg: rgba(201,138,75,0.14);
      --green: #3c7a5c;
      --green-bg: rgba(60,122,92,0.10);
      --red: #a8452f;
      --red-bg: rgba(168,69,47,0.10);
    }
    html[data-theme="dark"] {
      --paper: #0b0e11;
      --paper-alt: #161a1e;
      --ink: #eaecef;
      --ink-dim: #848e9c;
      --ink-faint: #5e6673;
      --hairline: #262b31;
      --periwinkle: #93a4e8;
      --periwinkle-bg: rgba(147,164,232,0.14);
      --tan: #f0b90b;
      --tan-bg: rgba(240,185,11,0.14);
      --green: #0ecb81;
      --green-bg: rgba(14,203,129,0.12);
      --red: #f6465d;
      --red-bg: rgba(246,70,93,0.12);
    }
    * { box-sizing: border-box; }
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      min-height: 100vh;
      transition: background 0.2s ease, color 0.2s ease;
    }
    .serif { font-family: 'Fraunces', Georgia, serif; }
    .mono { font-family: 'JetBrains Mono', monospace; }
    .wrap { max-width: 1160px; margin: 0 auto; padding: 40px 24px 70px; }

    .icon {
      font-family: 'Material Symbols Rounded';
      font-weight: normal; font-style: normal;
      font-size: 20px; line-height: 1; letter-spacing: normal; text-transform: none;
      white-space: nowrap; word-wrap: normal; direction: ltr;
      -webkit-font-smoothing: antialiased;
      font-variation-settings: 'FILL' 1, 'wght' 500, 'GRAD' 0, 'opsz' 24;
      vertical-align: middle; display: inline-block;
    }

    .kicker { font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--ink-faint); margin-bottom: 10px; }

    .topbar { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 8px; flex-wrap: wrap; gap: 16px; border-bottom: 1px solid var(--hairline); padding-bottom: 24px; }
    .brand-row { display: flex; align-items: center; gap: 12px; }
    .logo-badge { width: 46px; height: 46px; display: flex; align-items: center; justify-content: center; flex: none; }
    .logo-badge img { width: 100%; height: 100%; object-fit: contain; }
    .brand h1 { font-size: 30px; font-weight: 500; margin: 0; letter-spacing: -0.01em; }
    .brand .sub { font-size: 13px; color: var(--ink-dim); margin-top: 4px; }

    .topbar-actions { display: flex; align-items: center; gap: 10px; }
    .theme-toggle {
      width: 38px; height: 38px; border-radius: 100px; border: 1px solid var(--hairline);
      background: var(--paper-alt); color: var(--ink-dim); display: inline-flex; align-items: center; justify-content: center;
      cursor: pointer; transition: color 0.15s, border-color 0.15s;
    }
    .theme-toggle:hover { color: var(--ink); border-color: var(--ink-faint); }
    .theme-toggle .icon-sun { display: none; }
    .theme-toggle .icon-moon { display: inline-block; }
    html[data-theme="dark"] .theme-toggle .icon-sun { display: inline-block; }
    html[data-theme="dark"] .theme-toggle .icon-moon { display: none; }

    .pill { display: inline-flex; align-items: center; gap: 7px; padding: 7px 14px; border-radius: 100px; font-size: 12px; font-weight: 500; border: 1px solid var(--hairline); background: var(--paper-alt); }
    .pill .dot { width: 6px; height: 6px; border-radius: 50%; }
    .pill-live { color: var(--red); border-color: rgba(168,69,47,0.3); }
    .pill-live .dot { background: var(--red); box-shadow: 0 0 0 0 rgba(168,69,47,0.4); animation: pulse 1.8s infinite; }
    .pill-dry { color: var(--tan); border-color: rgba(201,138,75,0.35); }
    .pill-dry .dot { background: var(--tan); }
    @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(168,69,47,0.4); } 70% { box-shadow: 0 0 0 6px rgba(168,69,47,0); } 100% { box-shadow: 0 0 0 0 rgba(168,69,47,0); } }

    .strategy-row { display: flex; gap: 22px; flex-wrap: wrap; padding: 20px 0 32px; font-size: 13px; color: var(--ink-dim); }
    .strategy-row .item b { color: var(--ink); font-weight: 600; }
    .strategy-row .item .lbl { display: block; font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--ink-faint); margin-bottom: 3px; }

    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-bottom: 8px; }
    .stat { padding: 18px 20px; border: 1px solid var(--hairline); border-radius: 12px; background: var(--paper-alt); }
    .stat .label { font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--ink-faint); margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }
    .stat .label .icon { font-size: 15px; }
    .stat .value { font-family: 'Fraunces', Georgia, serif; font-size: 28px; font-weight: 500; letter-spacing: -0.01em; font-variant-numeric: oldstyle-nums; }
    .stat .value.green { color: var(--green); }
    .stat .value.red { color: var(--red); }
    .stat .value.warn { color: var(--tan); }
    .stat .foot { font-size: 11.5px; color: var(--ink-dim); margin-top: 6px; }
    .stat .foot.warn { color: var(--tan); }
    .stat .today-pnl { display: flex; align-items: center; gap: 5px; font-size: 11.5px; font-weight: 600; margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--hairline); }
    .stat .today-pnl .icon { font-size: 14px; }
    .stat .today-pnl.green { color: var(--green); }
    .stat .today-pnl.red { color: var(--red); }

    .section { padding: 40px 0; border-bottom: 1px solid var(--hairline); }
    .section-head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 20px; }
    .section-head h2 { font-family: 'Fraunces', Georgia, serif; font-size: 20px; font-weight: 500; margin: 0; display: flex; align-items: center; gap: 8px; }
    .section-head h2 .icon { font-size: 19px; color: var(--ink-faint); }
    .section-head .count { font-size: 12px; color: var(--ink-faint); }

    table { border-collapse: collapse; width: 100%; }
    th, td { padding: 12px 6px; text-align: left; font-size: 13px; white-space: nowrap; }
    th { color: var(--ink-faint); font-weight: 500; font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.06em; border-bottom: 1px solid var(--hairline); padding-bottom: 10px; }
    tbody tr { border-bottom: 1px solid var(--hairline); }
    tbody tr:last-child { border-bottom: none; }
    tbody tr:hover { background: var(--paper-alt); }
    td.num { font-family: 'JetBrains Mono', monospace; }
    .sym { font-weight: 600; display: inline-flex; align-items: center; }
    .sym .tick { color: var(--ink-faint); font-weight: 400; font-family: 'JetBrains Mono', monospace; font-size: 11px; margin-left: 4px; }
    .coin-badge {
      width: 22px; height: 22px; border-radius: 50%; background: var(--periwinkle-bg); color: var(--periwinkle);
      display: inline-flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700;
      margin-right: 8px; flex: none;
    }

    .tag { display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 500; }
    .tag .icon { font-size: 15px; }
    .tag-tp { color: var(--green); }
    .tag-sl { color: var(--red); }

    .pos { color: var(--green); }
    .neg { color: var(--red); }

    .empty { padding: 44px 6px; color: var(--ink-faint); font-size: 13px; font-style: italic; }

    .equity-svg { width: 100%; height: 130px; display: block; }
    .equity-svg .zero-line { stroke: var(--hairline); }
    .equity-svg .line.pos { stroke: var(--green); }
    .equity-svg .line.neg { stroke: var(--red); }
    .equity-svg .dot.pos { fill: var(--green); }
    .equity-svg .dot.neg { fill: var(--red); }
    .chart-caption { font-size: 12px; color: var(--ink-dim); font-style: italic; margin-top: 12px; }

    .mover-bar { width: 160px; height: 6px; border-radius: 100px; background: var(--hairline); overflow: hidden; }
    .mover-bar-fill { height: 100%; border-radius: 100px; }
    .mover-bar-fill.cool { background: var(--periwinkle); opacity: 0.6; }
    .mover-bar-fill.warm { background: var(--tan); }
    .mover-bar-fill.hot { background: var(--green); }

    footer { text-align: center; color: var(--ink-faint); font-size: 11px; margin-top: 32px; }

    .table-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }
    .table-scroll table { min-width: 640px; }

    @media (max-width: 640px) {
      .wrap { padding: 28px 16px 50px; }
      .brand h1 { font-size: 23px; }
      .brand .sub { font-size: 12px; }
      .stat .value { font-size: 24px; }
      .section { padding: 28px 0; }
      .section-head h2 { font-size: 17px; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="kicker">{{ now_label }} &middot; live strategy monitor</div>
    <div class="topbar">
      <div class="brand-row">
        <div class="logo-badge"><img src="/static/logo.png" alt="Coinbase Bot logo"></div>
        <div class="brand">
          <h1 class="serif">Coinbase Bot</h1>
          <div class="sub">Scanning {{ product_count }} USD/USDC pairs &middot; updated <span id="ts">just now</span></div>
        </div>
      </div>
      <div class="topbar-actions">
        {% if dry_run %}
        <div class="pill pill-dry"><span class="dot"></span>Dry run — no live orders</div>
        {% else %}
        <div class="pill pill-live"><span class="dot"></span>Live — trading real funds</div>
        {% endif %}
        <button class="theme-toggle" onclick="toggleTheme()" aria-label="Toggle color theme" title="Toggle color theme">
          <span class="icon icon-sun">light_mode</span>
          <span class="icon icon-moon">dark_mode</span>
        </button>
      </div>
    </div>

    <div id="stats">{{ stats_html|safe }}</div>

    <div class="strategy-row">
      <div class="item"><span class="lbl">Buy trigger</span><b>+{{ cfg.pump_threshold_pct|int }}% / {{ cfg.pump_window_minutes }}m</b></div>
      <div class="item"><span class="lbl">Take profit</span><b>+{{ cfg.take_profit_pct|int }}%</b></div>
      <div class="item"><span class="lbl">Stop loss</span><b>&minus;{{ cfg.stop_loss_pct|int }}%</b></div>
      <div class="item"><span class="lbl">Position size</span><b>${{ '%.0f'|format(cfg.position_size_usd) }} / coin</b></div>
      <div class="item"><span class="lbl">Poll interval</span><b>{{ cfg.poll_interval_seconds }}s</b></div>
    </div>

    <div class="section">
      <div class="section-head"><h2><span class="icon">bolt</span>Top movers</h2><span class="count">live, right now</span></div>
      <div id="top-movers" class="table-scroll">{{ top_movers_html|safe }}</div>
    </div>

    <div class="section">
      <div class="section-head"><h2><span class="icon">show_chart</span>Equity curve</h2><span class="count">realized P&amp;L over time</span></div>
      {{ equity_svg|safe }}
    </div>

    <div class="section">
      <div class="section-head"><h2><span class="icon">radar</span>Open positions</h2><span class="count">{{ open_positions|length }} active</span></div>
      <div id="open-table" class="table-scroll">{{ open_table_html|safe }}</div>
    </div>

    <div class="section" style="border-bottom: none;">
      <div class="section-head"><h2><span class="icon">receipt_long</span>Closed trades</h2><span class="count">{{ closed_positions|length }} total</span></div>
      <div id="closed-table" class="table-scroll">{{ closed_table_html|safe }}</div>
    </div>

    <footer>Coinbase Bot &middot; dashboard refreshes every 5 seconds</footer>
  </div>

  <script>
    function toggleTheme() {
      var html = document.documentElement;
      var next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-theme', next);
      try { localStorage.setItem('cmb-theme', next); } catch (e) {}
    }
    async function refresh() {
      try {
        const res = await fetch('/api/render');
        const data = await res.json();
        document.getElementById('stats').innerHTML = data.stats_html;
        document.getElementById('top-movers').innerHTML = data.top_movers_html;
        document.getElementById('open-table').innerHTML = data.open_table_html;
        document.getElementById('closed-table').innerHTML = data.closed_table_html;
        document.getElementById('ts').textContent = new Date().toLocaleTimeString();
      } catch (e) { /* keep last good render */ }
    }
    setInterval(refresh, 5000);
  </script>
</body>
</html>
"""


def _todays_pnl(closed_positions):
    start_of_day = dt.datetime.combine(dt.date.today(), dt.time.min).timestamp()
    todays = [p for p in closed_positions if p["exit_time"] and p["exit_time"] >= start_of_day]
    return sum((p["pnl_usd"] or 0) for p in todays), len(todays)


def _render_stats(open_positions, closed_positions, balance, position_size_usd) -> str:
    total_pnl = sum((p["pnl_usd"] or 0) for p in closed_positions)
    wins = sum(1 for p in closed_positions if (p["pnl_usd"] or 0) > 0)
    win_rate = (wins / len(closed_positions) * 100) if closed_positions else 0.0
    open_exposure = sum(p["usd_size"] for p in open_positions)
    today_pnl, today_count = _todays_pnl(closed_positions)

    pnl_cls = "green" if total_pnl >= 0 else "red"
    today_cls = "green" if today_pnl >= 0 else "red"

    if balance is None:
        balance_value = "&mdash;"
        balance_foot = "unable to fetch balance"
        balance_foot_cls = "warn"
    else:
        balance_value = f"${balance:,.2f}"
        if balance < position_size_usd:
            balance_foot = f"below ${position_size_usd:,.0f} position size"
            balance_foot_cls = "warn"
        else:
            balance_foot = "available to trade"
            balance_foot_cls = ""

    return f"""
    <div class="grid">
      <div class="stat">
        <div class="label"><span class="icon">account_balance</span>Balance</div>
        <div class="value">{balance_value}</div>
        <div class="foot {balance_foot_cls}">{balance_foot}</div>
        <div class="today-pnl {today_cls}"><span class="icon">today</span>Today {_fmt_usd(today_pnl)} &middot; {today_count} trade{'s' if today_count != 1 else ''}</div>
      </div>
      <div class="stat">
        <div class="label"><span class="icon">paid</span>Total P&amp;L</div>
        <div class="value {pnl_cls}">{_fmt_usd(total_pnl)}</div>
        <div class="foot">realized, all time</div>
      </div>
      <div class="stat">
        <div class="label"><span class="icon">target</span>Win rate</div>
        <div class="value">{win_rate:.0f}%</div>
        <div class="foot">of closed trades</div>
      </div>
      <div class="stat">
        <div class="label"><span class="icon">stacks</span>Open positions</div>
        <div class="value">{len(open_positions)}</div>
        <div class="foot">${open_exposure:,.2f} exposed</div>
      </div>
      <div class="stat">
        <div class="label"><span class="icon">history</span>Closed trades</div>
        <div class="value">{len(closed_positions)}</div>
        <div class="foot">{wins} wins &middot; {len(closed_positions) - wins} losses</div>
      </div>
    </div>
    """


def _render_equity_svg(closed_positions) -> str:
    ordered = sorted(closed_positions, key=lambda p: p["exit_time"] or 0)
    if len(ordered) < 2:
        return '<div class="empty">Equity curve appears once there are 2 or more closed trades.</div>'

    cumulative = []
    running = 0.0
    for p in ordered:
        running += p["pnl_usd"] or 0
        cumulative.append(running)

    width, height, pad = 1100, 130, 12
    lo, hi = min(0.0, min(cumulative)), max(0.0, max(cumulative))
    span = (hi - lo) or 1.0
    n = len(cumulative)
    step = (width - 2 * pad) / (n - 1)

    points = []
    for i, v in enumerate(cumulative):
        x = pad + i * step
        y = height - pad - ((v - lo) / span) * (height - 2 * pad)
        points.append((x, y))

    zero_y = height - pad - ((0 - lo) / span) * (height - 2 * pad)
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    sign_cls = "pos" if cumulative[-1] >= 0 else "neg"

    last_x, last_y = points[-1]

    svg = f"""
    <svg class="equity-svg" viewBox="0 0 {width} {height}" preserveAspectRatio="none">
      <line class="zero-line" x1="{pad}" y1="{zero_y:.1f}" x2="{width - pad}" y2="{zero_y:.1f}" stroke-width="1" stroke-dasharray="3 5"/>
      <polyline class="line {sign_cls}" points="{line}" fill="none" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
      <circle class="dot {sign_cls}" cx="{last_x:.1f}" cy="{last_y:.1f}" r="3"/>
    </svg>
    """
    caption = f"Final realized P&amp;L: {_fmt_usd(cumulative[-1])} across {len(cumulative)} closed trades."
    return svg + f'<div class="chart-caption">{caption}</div>'


def _render_open_table(open_positions, price_lookup) -> str:
    if not open_positions:
        return '<div class="empty">No open positions — scanning for a 15% move in 15 minutes.</div>'

    rows = []
    for p in open_positions:
        current_price = price_lookup.get(p["product_id"])
        if current_price is not None:
            unrealized_pct = ((current_price - p["entry_price"]) / p["entry_price"]) * 100
            unrealized_usd = (current_price - p["entry_price"]) * p["quantity"]
            cls = "pos" if unrealized_usd >= 0 else "neg"
            live_cols = f"""
              <td class="num">{current_price:.6f}</td>
              <td class="num {cls}">{_fmt_usd(unrealized_usd)}</td>
              <td class="num {cls}">{unrealized_pct:+.2f}%</td>
            """
        else:
            live_cols = '<td class="num">&mdash;</td><td class="num">&mdash;</td><td class="num">&mdash;</td>'

        entry_time = dt.datetime.fromtimestamp(p["entry_time"]).strftime("%H:%M:%S")
        base, quote = (p["product_id"].split("-") + [""])[:2]
        rows.append(f"""
        <tr>
          <td><span class="sym"><span class="coin-badge">{base[:1]}</span>{base}<span class="tick">/{quote}</span></span></td>
          <td class="num">{p['entry_price']:.6f}</td>
          <td class="num">{p['quantity']:.6f}</td>
          <td class="num">${p['usd_size']:.2f}</td>
          {live_cols}
          <td>{entry_time}</td>
        </tr>
        """)

    return f"""
    <table>
      <thead><tr>
        <th>Product</th><th>Entry price</th><th>Quantity</th><th>USD size</th>
        <th>Current price</th><th>Unrealized P&amp;L</th><th>Unrealized %</th><th>Entry time</th>
      </tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    """


def _render_closed_table(closed_positions) -> str:
    if not closed_positions:
        return '<div class="empty">No closed trades yet.</div>'

    rows = []
    for p in closed_positions:
        tag = (
            '<span class="tag tag-tp"><span class="icon">trending_up</span>Take profit</span>'
            if p["exit_reason"] == "take_profit"
            else '<span class="tag tag-sl"><span class="icon">trending_down</span>Stop loss</span>'
        )
        cls_usd = "pos" if (p["pnl_usd"] or 0) >= 0 else "neg"
        cls_pct = "pos" if (p["pnl_pct"] or 0) >= 0 else "neg"
        exit_time = dt.datetime.fromtimestamp(p["exit_time"]).strftime("%H:%M:%S") if p["exit_time"] else "—"
        base, quote = (p["product_id"].split("-") + [""])[:2]
        rows.append(f"""
        <tr>
          <td><span class="sym"><span class="coin-badge">{base[:1]}</span>{base}<span class="tick">/{quote}</span></span></td>
          <td class="num">{p['entry_price']:.6f}</td>
          <td class="num">{p['exit_price']:.6f}</td>
          <td>{tag}</td>
          <td class="num {cls_usd}">{_fmt_usd(p['pnl_usd'])}</td>
          <td class="num {cls_pct}">{p['pnl_pct']:+.2f}%</td>
          <td>{exit_time}</td>
        </tr>
        """)

    return f"""
    <table>
      <thead><tr>
        <th>Product</th><th>Entry</th><th>Exit</th><th>Reason</th><th>P&amp;L $</th><th>P&amp;L %</th><th>Exit time</th>
      </tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    """


def _render_top_movers(snapshot, threshold_pct) -> str:
    top_movers = snapshot.get("top_movers") or []
    scan_seconds = snapshot.get("scan_seconds")
    products_scanned = snapshot.get("products_scanned") or 0

    if scan_seconds is not None:
        caption = f"{products_scanned} products scanned in {scan_seconds:.1f}s"
    else:
        caption = "First scan in progress..."

    if not top_movers:
        return f'<div class="empty">No market data yet. {caption}</div>'

    rows = []
    for m in top_movers:
        pct = m["pct_change"]
        base, quote = (m["product_id"].split("-") + [""])[:2]
        progress = max(0.0, min(100.0, (pct / threshold_pct) * 100)) if threshold_pct else 0
        if pct >= threshold_pct:
            bar_cls, pct_cls = "hot", "pos"
        elif progress >= 60:
            bar_cls, pct_cls = "warm", ""
        else:
            bar_cls, pct_cls = "cool", ""

        rows.append(f"""
        <tr>
          <td><span class="sym"><span class="coin-badge">{base[:1]}</span>{base}<span class="tick">/{quote}</span></span></td>
          <td class="num {pct_cls}">{pct:+.2f}%</td>
          <td>
            <div class="mover-bar">
              <div class="mover-bar-fill {bar_cls}" style="width:{progress:.0f}%"></div>
            </div>
          </td>
        </tr>
        """)

    return f"""
    <table>
      <thead><tr><th>Product</th><th>15m change</th><th>Progress to +{threshold_pct:.0f}% trigger</th></tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    <div class="chart-caption">{caption}</div>
    """


def create_app(store: PositionStore, client=None, config: Config = None, market_state=None) -> Flask:
    app = Flask(__name__)
    config = config or Config()

    @app.before_request
    def _auth_guard():
        if not config.dashboard_user:
            return None
        auth = request.authorization
        valid = (
            auth is not None
            and hmac.compare_digest(auth.username, config.dashboard_user)
            and hmac.compare_digest(auth.password, config.dashboard_password)
        )
        if not valid:
            return Response(
                "Authentication required",
                401,
                {"WWW-Authenticate": 'Basic realm="Coinbase Bot"'},
            )
        return None

    def _price_lookup(open_positions):
        lookup = {}
        if client is None:
            return lookup
        for p in open_positions:
            try:
                lookup[p["product_id"]] = client.get_current_price(p["product_id"])
            except Exception:
                continue
        return lookup

    def _get_balance():
        if client is None:
            return None
        try:
            return client.get_usd_balance()
        except Exception:
            return None

    def _fragments():
        open_positions = store.get_open_positions()
        closed_positions = store.get_closed_positions()
        prices = _price_lookup(open_positions)
        balance = _get_balance()
        snapshot = market_state.snapshot() if market_state is not None else {}
        return {
            "stats_html": _render_stats(open_positions, closed_positions, balance, config.position_size_usd),
            "top_movers_html": _render_top_movers(snapshot, config.pump_threshold_pct),
            "open_table_html": _render_open_table(open_positions, prices),
            "closed_table_html": _render_closed_table(closed_positions),
            "equity_svg": _render_equity_svg(closed_positions),
            "open_positions": open_positions,
            "closed_positions": closed_positions,
            "products_scanned": snapshot.get("products_scanned", 0),
        }

    @app.route("/")
    def index():
        frag = _fragments()
        return render_template_string(
            PAGE,
            cfg=config,
            dry_run=config.dry_run,
            product_count=frag["products_scanned"],
            now_label=dt.datetime.now().strftime("%B %d, %Y").upper(),
            **frag,
        )

    @app.route("/api/render")
    def api_render():
        frag = _fragments()
        return jsonify(
            {
                "stats_html": frag["stats_html"],
                "top_movers_html": frag["top_movers_html"],
                "open_table_html": frag["open_table_html"],
                "closed_table_html": frag["closed_table_html"],
            }
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
