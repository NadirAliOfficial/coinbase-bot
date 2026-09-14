def take_profit_price(entry_price: float, take_profit_pct: float) -> float:
    return entry_price * (1 + take_profit_pct / 100)


def stop_loss_price(entry_price: float, stop_loss_pct: float) -> float:
    return entry_price * (1 - stop_loss_pct / 100)


def should_take_profit(current_price: float, entry_price: float, take_profit_pct: float) -> bool:
    return current_price >= take_profit_price(entry_price, take_profit_pct)


def should_stop_loss(current_price: float, entry_price: float, stop_loss_pct: float) -> bool:
    return current_price <= stop_loss_price(entry_price, stop_loss_pct)


def pnl_usd(entry_price: float, exit_price: float, quantity: float) -> float:
    return (exit_price - entry_price) * quantity


def pnl_pct(entry_price: float, exit_price: float) -> float:
    return ((exit_price - entry_price) / entry_price) * 100
