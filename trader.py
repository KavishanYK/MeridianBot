"""
trader.py – Order execution and open-position management (multi-symbol).

Positions are tracked per-symbol. main.py calls:
    trader.execute(signal, current_price, symbol, atr)   – on each candle close
  trader.check_exit_on_price(current_price, symbol) – intra-candle SL/TP check

Events are appended to `event_log` (a deque) instead of printed directly,
so the Rich UI in main.py can display them without corrupting the display.
"""

from collections import deque
from datetime import datetime, timezone
import exchange
import risk_manager
import logger
import config
from strategy import Signal


# ── In-memory position state keyed by symbol ─────────────────────────────────
_positions: dict[str, dict] = {}   # symbol → position dict  (absent = flat)

_daily_date: str | None = None
_daily_start_balance: float = 0.0
_daily_realized_pnl: float = 0.0
_consecutive_losses: int = 0
_pause_until_ts: float = 0.0

# ── Event log (drained each cycle by main.py) ────────────────────────────────
event_log: deque = deque(maxlen=100)


def _log(msg: str) -> None:
    event_log.append(msg)


def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()


def _roll_daily_guard(balance_usdt: float) -> None:
    global _daily_date, _daily_start_balance, _daily_realized_pnl, _consecutive_losses
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if _daily_date != today:
        _daily_date = today
        _daily_start_balance = balance_usdt
        _daily_realized_pnl = 0.0
        _consecutive_losses = 0


def _is_paused() -> bool:
    return _now_ts() < _pause_until_ts


def _daily_loss_hit() -> bool:
    if _daily_start_balance <= 0:
        return False
    return _daily_realized_pnl <= -(_daily_start_balance * config.DAILY_LOSS_LIMIT_PCT)


# ── Public API ────────────────────────────────────────────────────────────────

def has_position(symbol: str) -> bool:
    return symbol in _positions


def get_position(symbol: str) -> dict | None:
    return _positions.get(symbol)


def get_all_positions() -> dict[str, dict]:
    """Return a snapshot of all open positions."""
    return dict(_positions)


def can_open_new_position() -> bool:
    return (not _is_paused()) and (not _daily_loss_hit()) and len(_positions) < config.MAX_OPEN_POSITIONS


def execute(signal: Signal, current_price: float, symbol: str, atr: float) -> None:
    """Called once per candle close for the given symbol."""
    if has_position(symbol):
        _check_exit(current_price, symbol)
        return  # only one position per symbol at a time

    if signal == Signal.BUY:
        balance = exchange.get_balance("USDT")
        _roll_daily_guard(balance)

        if _is_paused():
            _log("[yellow]PAUSED[/yellow]  Consecutive-loss cooldown active")
            return
        if _daily_loss_hit():
            _log("[red]DAILY STOP[/red]  Daily loss limit reached; no new entries")
            return
        if len(_positions) >= config.MAX_OPEN_POSITIONS:
            _log("[yellow]SKIP[/yellow]  Max open positions reached")
            return

    if signal == Signal.BUY:
        _open_position(current_price, symbol, atr)
    # SELL while flat is ignored (spot-only bot)


def check_exit_on_price(current_price: float, symbol: str) -> None:
    """Intra-candle SL/TP check."""
    if has_position(symbol):
        _check_exit(current_price, symbol)


# ── Internals ─────────────────────────────────────────────────────────────────

def _open_position(entry_price: float, symbol: str, atr: float) -> None:
    balance = exchange.get_balance("USDT")
    sizing  = risk_manager.calculate_position(balance, entry_price, atr)

    if sizing["qty"] <= 0:
        _log(f"[yellow]SKIP[/yellow]  [cyan]{symbol}[/cyan]  "
             f"Insufficient balance ({balance:.2f} USDT)")
        return

    _log(f"[green]BUY[/green]  [cyan]{symbol}[/cyan]  "
         f"{sizing['qty']} @ {entry_price:.2f}  "
            f"SL={sizing['stop_loss']}  TP1={sizing['tp1']}  TP2={sizing['tp2']}")

    order = exchange.place_market_order(symbol, "buy", sizing["qty"])

    _positions[symbol] = {
        "entry_price": entry_price,
        "qty":         sizing["qty"],
        "remaining_qty": sizing["qty"],
        "stop_loss":   sizing["stop_loss"],
        "take_profit": sizing["tp2"],
        "tp1":         sizing["tp1"],
        "tp2":         sizing["tp2"],
        "trail_offset": sizing["trail_offset"],
        "atr":         atr,
        "tp1_hit":     False,
        "highest_price": entry_price,
        "order_id":    order.get("id"),
    }

    logger.log_trade(
        symbol   = symbol,
        side     = "BUY",
        price    = entry_price,
        qty      = sizing["qty"],
        order_id = str(order.get("id")),
    )


def _close_position(close_price: float, reason: str, symbol: str, qty_to_close: float | None = None) -> None:
    global _daily_realized_pnl, _consecutive_losses, _pause_until_ts

    pos = _positions.get(symbol)
    if pos is None:
        return

    qty         = qty_to_close if qty_to_close is not None else pos["remaining_qty"]
    qty = min(qty, pos["remaining_qty"])
    qty = round(qty, 5)
    if qty <= 0:
        return

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

    _daily_realized_pnl += pnl
    if pnl < 0:
        _consecutive_losses += 1
    else:
        _consecutive_losses = 0

    if _consecutive_losses >= config.MAX_CONSECUTIVE_LOSSES:
        _pause_until_ts = _now_ts() + config.CONSECUTIVE_LOSS_PAUSE_SECONDS
        _consecutive_losses = 0
        _log("[yellow]PAUSE[/yellow]  3 consecutive losses hit; pausing entries for 1 hour")

    pos["remaining_qty"] = round(pos["remaining_qty"] - qty, 5)
    if pos["remaining_qty"] <= 0:
        del _positions[symbol]


def _check_exit(current_price: float, symbol: str) -> None:
    pos = _positions.get(symbol)
    if pos is None:
        return

    pos["highest_price"] = max(pos.get("highest_price", current_price), current_price)

    if risk_manager.should_stop_loss(current_price, pos["stop_loss"]):
        _close_position(current_price, "CLOSE_SL", symbol)
        return

    if (not pos.get("tp1_hit")) and risk_manager.should_take_profit(current_price, pos["tp1"]):
        qty_half = round(pos["qty"] * 0.5, 5)
        _close_position(current_price, "CLOSE_TP1", symbol, qty_to_close=qty_half)

        pos = _positions.get(symbol)
        if pos is None:
            return

        pos["tp1_hit"] = True
        # Move stop to breakeven and activate trailing behavior.
        pos["stop_loss"] = max(pos["stop_loss"], pos["entry_price"])

    pos = _positions.get(symbol)
    if pos is None:
        return

    if pos.get("tp1_hit"):
        trailing_stop = pos["highest_price"] - pos["trail_offset"]
        pos["stop_loss"] = max(pos["stop_loss"], round(trailing_stop, 2))

    if risk_manager.should_take_profit(current_price, pos["tp2"]):
        _close_position(current_price, "CLOSE_TP2", symbol)
