"""
trader.py – Order execution and open-position management (multi-symbol).

Positions are tracked per-symbol. main.py calls:
  trader.execute(signal, current_price, symbol)   – on each candle close
  trader.check_exit_on_price(current_price, symbol) – intra-candle SL/TP check

Events are appended to `event_log` (a deque) instead of printed directly,
so the Rich UI in main.py can display them without corrupting the display.
"""

from collections import deque
import exchange
import risk_manager
import logger
import config
from strategy import Signal


# ── In-memory position state keyed by symbol ─────────────────────────────────
_positions: dict[str, dict] = {}   # symbol → position dict  (absent = flat)

# ── Event log (drained each cycle by main.py) ────────────────────────────────
event_log: deque = deque(maxlen=100)


def _log(msg: str) -> None:
    event_log.append(msg)


# ── Public API ────────────────────────────────────────────────────────────────

def has_position(symbol: str) -> bool:
    return symbol in _positions


def get_position(symbol: str) -> dict | None:
    return _positions.get(symbol)


def get_all_positions() -> dict[str, dict]:
    """Return a snapshot of all open positions."""
    return dict(_positions)


def execute(signal: Signal, current_price: float, symbol: str) -> None:
    """Called once per candle close for the given symbol."""
    if has_position(symbol):
        _check_exit(current_price, symbol)
        return  # only one position per symbol at a time

    if signal == Signal.BUY:
        _open_position(current_price, symbol)
    # SELL while flat is ignored (spot-only bot)


def check_exit_on_price(current_price: float, symbol: str) -> None:
    """Intra-candle SL/TP check."""
    if has_position(symbol):
        _check_exit(current_price, symbol)


# ── Internals ─────────────────────────────────────────────────────────────────

def _open_position(entry_price: float, symbol: str) -> None:
    balance = exchange.get_balance("USDT")
    sizing  = risk_manager.calculate_position(balance, entry_price)

    if sizing["qty"] <= 0:
        _log(f"[yellow]SKIP[/yellow]  [cyan]{symbol}[/cyan]  "
             f"Insufficient balance ({balance:.2f} USDT)")
        return

    _log(f"[green]BUY[/green]  [cyan]{symbol}[/cyan]  "
         f"{sizing['qty']} @ {entry_price:.2f}  "
         f"SL={sizing['stop_loss']}  TP={sizing['take_profit']}")

    order = exchange.place_market_order(symbol, "buy", sizing["qty"])

    _positions[symbol] = {
        "entry_price": entry_price,
        "qty":         sizing["qty"],
        "stop_loss":   sizing["stop_loss"],
        "take_profit": sizing["take_profit"],
        "order_id":    order.get("id"),
    }

    logger.log_trade(
        symbol   = symbol,
        side     = "BUY",
        price    = entry_price,
        qty      = sizing["qty"],
        order_id = str(order.get("id")),
    )


def _close_position(close_price: float, reason: str, symbol: str) -> None:
    pos = _positions.get(symbol)
    if pos is None:
        return

    qty         = pos["qty"]
    entry_price = pos["entry_price"]
    pnl         = round((close_price - entry_price) * qty, 4)
    color       = "green" if pnl >= 0 else "red"

    _log(f"[{color}]{reason}[/{color}]  [cyan]{symbol}[/cyan]  "
         f"{qty} @ {close_price:.2f}  PnL=[{color}]{pnl:+.4f}[/{color}] USDT")

    order = exchange.place_market_order(symbol, "sell", qty)

    logger.log_trade(
        symbol   = symbol,
        side     = reason,
        price    = close_price,
        qty      = qty,
        pnl_usdt = pnl,
        order_id = str(order.get("id")),
    )

    del _positions[symbol]


def _check_exit(current_price: float, symbol: str) -> None:
    pos = _positions.get(symbol)
    if pos is None:
        return

    if risk_manager.should_stop_loss(current_price, pos["stop_loss"]):
        _close_position(current_price, "CLOSE_SL", symbol)
    elif risk_manager.should_take_profit(current_price, pos["take_profit"]):
        _close_position(current_price, "CLOSE_TP", symbol)
